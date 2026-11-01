/**
 * @file main.c
 * @brief Smart Parking System - ESP32 Firmware Core Application
 * 
 * KIẾN TRÚC ĐA NHIỆM FREERTOS CHUẨN CÔNG NGHIỆP:
 * 1. sensor_task (Core 1, Priority 5): Đọc 4 cảm biến siêu âm HC-SR04, áp dụng bộ lọc & hysteresis
 * 2. rfid_task (Core 1, Priority 6): Quét thẻ 2 đầu đọc MFRC522 qua SPI, xác thực backend và mở cổng
 * 3. barrier_task (Core 0, Priority 4): Máy trạng thái đếm lùi non-blocking, giám sát chùm tia quang an toàn
 * 4. network_task (Core 0, Priority 3): Đồng bộ telemetry cảm biến lên FastAPI REST API
 * 5. display_task (Core 0, Priority 2): Cập nhật màn hình LCD 1602 I2C
 * 
 * BẢO VỆ ĐỒNG BỘ:
 * - FreeRTOS Mutex (g_telemetry_mutex) bảo vệ an toàn luồng khi chia sẻ dữ liệu ô đỗ giữa Core 0 và Core 1.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_system.h"

#include "parking_types.h"
#include "pin_config.h"
#include "ultrasonic_sensor.h"
#include "rfid_reader.h"
#include "barrier_controller.h"
#include "network_client.h"
#include "display_lcd.h"

static const char *TAG = "MAIN_APP";

// Biến chia sẻ toàn cục trạng thái 4 ô đỗ và khóa Mutex
static slot_telemetry_t g_slots[MAX_SLOTS];
static SemaphoreHandle_t g_telemetry_mutex = NULL;

// ==============================================================================
// FREERTOS TASKS
// ==============================================================================

/**
 * @brief Tác vụ đọc cảm biến siêu âm trên Core 1 (Ưu tiên cao).
 */
static void sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Sensor task active on Core %d", xPortGetCoreID());
    slot_telemetry_t local_slots[MAX_SLOTS];

    while (1) {
        // Đọc phần cứng tuần tự
        ultrasonic_sensor_read_all(local_slots);

        // Cập nhật vào vùng nhớ chia sẻ với khóa Mutex
        if (g_telemetry_mutex && xSemaphoreTake(g_telemetry_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            memcpy(g_slots, local_slots, sizeof(g_slots));
            xSemaphoreGive(g_telemetry_mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

/**
 * @brief Tác vụ quét thẻ RFID trên Core 1 (Ưu tiên cao nhất).
 */
static void rfid_task(void *pvParameters) {
    ESP_LOGI(TAG, "RFID polling task active on Core %d", xPortGetCoreID());
    char card_uid[32];

    while (1) {
        // 1. Quét đầu đọc Cổng Vào
        if (rfid_reader_poll(GATE_ENTRY, card_uid, sizeof(card_uid)) == ESP_OK) {
            ESP_LOGI(TAG, ">>> ENTRY TAP: Card UID = %s <<<", card_uid);
            display_lcd_show_status(4, "ENTRY TAP CHECK");

            bool allowed = false;
            char msg[64] = {0};
            esp_err_t net_ret = network_send_rfid_tap(GATE_ENTRY, card_uid, &allowed, msg, sizeof(msg));

            if (net_ret == ESP_OK && allowed) {
                ESP_LOGI(TAG, "Entry Granted! Raising barrier.");
                display_lcd_show_status(4, "WELCOME! OPEN");
                barrier_open(GATE_ENTRY);
            } else {
                ESP_LOGW(TAG, "Entry Denied: %s", msg);
                display_lcd_show_status(4, "ACCESS DENIED");
            }

            // Chờ nhả thẻ để tránh quét lặp liên tục
            vTaskDelay(pdMS_TO_TICKS(1000));
        }

        // 2. Quét đầu đọc Cổng Ra
        if (rfid_reader_poll(GATE_EXIT, card_uid, sizeof(card_uid)) == ESP_OK) {
            ESP_LOGI(TAG, ">>> EXIT TAP: Card UID = %s <<<", card_uid);
            display_lcd_show_status(4, "EXIT TAP CHECK");

            bool allowed = false;
            char msg[64] = {0};
            esp_err_t net_ret = network_send_rfid_tap(GATE_EXIT, card_uid, &allowed, msg, sizeof(msg));

            if (net_ret == ESP_OK && allowed) {
                ESP_LOGI(TAG, "Exit Granted! Raising barrier.");
                display_lcd_show_status(4, "GOODBYE! OPEN");
                barrier_open(GATE_EXIT);
            } else {
                ESP_LOGW(TAG, "Exit Denied: %s", msg);
                display_lcd_show_status(4, "ACCESS DENIED");
            }

            vTaskDelay(pdMS_TO_TICKS(1000));
        }

        vTaskDelay(pdMS_TO_TICKS(150));
    }
}

/**
 * @brief Tác vụ giám sát cảm biến an toàn và điều khiển đóng barrier (Core 0).
 */
static void barrier_task(void *pvParameters) {
    ESP_LOGI(TAG, "Barrier safety monitor task active on Core %d", xPortGetCoreID());
    uint32_t clear_counter_ms[2] = {0, 0};
    const uint32_t poll_interval_ms = 100;
    const uint32_t required_clear_ms = 3000;
    bool obstruction_logged[2] = {false, false};

    while (1) {
        for (int gate = 0; gate < 2; gate++) {
            if (barrier_get_state((gate_id_t)gate) == BARRIER_OPEN) {
                if (barrier_is_obstruction_detected((gate_id_t)gate)) {
                    // CÓ VẬT CẢN: Lập tức xóa bộ đếm đóng, bảo đảm không hạ barrier
                    clear_counter_ms[gate] = 0;
                    if (!obstruction_logged[gate]) {
                        ESP_LOGW(TAG, "Gate %s: Obstruction detected (IR Beam blocked)! SAFETY INTERLOCK ACTIVE: Barrier kept OPEN.",
                                 (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
                        obstruction_logged[gate] = true;
                    }
                } else {
                    // THÔNG THOÁNG: Tích lũy thời gian an toàn
                    if (obstruction_logged[gate]) {
                        ESP_LOGI(TAG, "Gate %s: Obstruction cleared. Resuming 3s safety close countdown.",
                                 (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
                        obstruction_logged[gate] = false;
                    }
                    clear_counter_ms[gate] += poll_interval_ms;
                    if (clear_counter_ms[gate] >= required_clear_ms) {
                        barrier_close((gate_id_t)gate);
                        clear_counter_ms[gate] = 0;
                    }
                }
            } else {
                clear_counter_ms[gate] = 0;
                obstruction_logged[gate] = false;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(poll_interval_ms));
    }
}

/**
 * @brief Tác vụ truyền thông gửi số liệu cảm biến lên Backend (Core 0).
 */
static void network_task(void *pvParameters) {
    ESP_LOGI(TAG, "Network telemetry task active on Core %d", xPortGetCoreID());
    slot_telemetry_t snapshot[MAX_SLOTS];

    while (1) {
        // Lấy snapshot dữ liệu an toàn với khóa Mutex
        if (g_telemetry_mutex && xSemaphoreTake(g_telemetry_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            memcpy(snapshot, g_slots, sizeof(snapshot));
            xSemaphoreGive(g_telemetry_mutex);

            // Gửi dữ liệu lên REST API Backend
            network_send_telemetry(snapshot);
        }

        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

/**
 * @brief Tác vụ cập nhật màn hình LCD 1602 (Core 0, Ưu tiên thấp).
 */
static void display_task(void *pvParameters) {
    ESP_LOGI(TAG, "Display LCD update task active on Core %d", xPortGetCoreID());

    while (1) {
        int free_slots = 0;
        if (g_telemetry_mutex && xSemaphoreTake(g_telemetry_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            for (int i = 0; i < MAX_SLOTS; i++) {
                if (!g_slots[i].occupied) free_slots++;
            }
            xSemaphoreGive(g_telemetry_mutex);
        }

        if (barrier_get_state(GATE_ENTRY) == BARRIER_OPEN) {
            if (barrier_is_obstruction_detected(GATE_ENTRY)) {
                display_lcd_show_status(free_slots, "ENTRY OBSTRUCT");
            } else {
                display_lcd_show_status(free_slots, "ENTRY GATE OPEN");
            }
        } else if (barrier_get_state(GATE_EXIT) == BARRIER_OPEN) {
            if (barrier_is_obstruction_detected(GATE_EXIT)) {
                display_lcd_show_status(free_slots, "EXIT OBSTRUCT");
            } else {
                display_lcd_show_status(free_slots, "EXIT GATE OPEN");
            }
        } else {
            display_lcd_show_status(free_slots, "PARKING ONLINE");
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

// ==============================================================================
// APPLICATION ENTRY POINT
// ==============================================================================

void app_main(void) {
#if defined(CONFIG_SMART_PARKING_WOKWI_DEMO_ONLY) || defined(CONFIG_SMART_PARKING_SIMULATION_OFFLINE_DEMO)
    ESP_LOGW(TAG, "============================================================");
    ESP_LOGW(TAG, "  MODE: WOKWI STANDALONE DEMO ONLY (OFFLINE OVERRIDE ACTIVE)");
    ESP_LOGW(TAG, "  WARNING: DO NOT FLASH THIS FIRMWARE TO PHYSICAL HARDWARE! ");
    ESP_LOGW(TAG, "  Whitelisted Demo Cards: Entry=30:A1:23:45 | Exit=01:02:03:04");
    ESP_LOGW(TAG, "============================================================");
#else
    ESP_LOGI(TAG, "============================================================");
    ESP_LOGI(TAG, "  MODE: HARDWARE PRODUCTION MODE (FAIL-SAFE STRICTLY ENFORCED)");
    ESP_LOGI(TAG, "  All barrier access strictly requires verified Backend authorization.");
    ESP_LOGI(TAG, "============================================================");
#endif

    // 1. Tạo khóa Mutex bảo vệ dữ liệu telemetry
    g_telemetry_mutex = xSemaphoreCreateMutex();
    if (!g_telemetry_mutex) {
        ESP_LOGE(TAG, "Failed to create telemetry mutex!");
    }

    // 2. Khởi tạo mảng ô đỗ mặc định
    for (int i = 0; i < MAX_SLOTS; i++) {
        snprintf(g_slots[i].slot_id, sizeof(g_slots[i].slot_id), "P0%d", i + 1);
        g_slots[i].distance_cm = 120.0f;
        g_slots[i].occupied = false;
        g_slots[i].last_update_ms = 0;
    }

    // 3. Khởi tạo các tầng trừu tượng phần cứng (HAL)
    ultrasonic_sensor_init();
    rfid_reader_init();
    barrier_controller_init();
    display_lcd_init();
    network_client_init();

    display_lcd_show_status(4, "SYSTEM READY");

    // 4. Khởi chạy các FreeRTOS Tasks trên cả 2 Core
    // Core 1: Dành riêng cho Realtime I/O (Cảm biến siêu âm & SPI RFID)
    xTaskCreatePinnedToCore(sensor_task, "sensor_task", 4096, NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(rfid_task, "rfid_task", 4096, NULL, 6, NULL, 1);

    // Core 0: Dành riêng cho Networking, Barrier Logic & LCD Display
    xTaskCreatePinnedToCore(barrier_task, "barrier_task", 3072, NULL, 4, NULL, 0);
    xTaskCreatePinnedToCore(network_task, "network_task", 4096, NULL, 3, NULL, 0);
    xTaskCreatePinnedToCore(display_task, "display_task", 3072, NULL, 2, NULL, 0);

    ESP_LOGI(TAG, "All 5 FreeRTOS Tasks successfully launched across Core 0 and Core 1.");
}
