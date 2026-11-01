/**
 * @file main.c
 * @brief Smart Parking System - ESP32 Firmware Core Application
 * 
 * Kiến trúc đa nhiệm FreeRTOS:
 * 1. sensor_task: Đọc 4 cảm biến siêu âm HC-SR04 định kỳ 500ms
 * 2. rfid_task: Lắng nghe sự kiện quẹt thẻ RFID tại cổng vào/ra
 * 3. barrier_task: Giám sát an toàn và điều khiển đóng/mở barrier
 * 4. network_task: Đồng bộ telemetry và nhận chỉ thị từ Backend
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
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

// Biến lưu trạng thái 4 ô đỗ
static slot_telemetry_t g_slots[MAX_SLOTS];

// ==============================================================================
// FREERTOS TASKS
// ==============================================================================

static void sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Sensor task started on Core %d", xPortGetCoreID());
    while (1) {
        ultrasonic_sensor_read_all(g_slots);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

static void rfid_task(void *pvParameters) {
    ESP_LOGI(TAG, "RFID task started on Core %d", xPortGetCoreID());
    char card_uid[32];
    while (1) {
        // Quét cổng vào
        if (rfid_reader_poll(GATE_ENTRY, card_uid, sizeof(card_uid)) == ESP_OK) {
            ESP_LOGI(TAG, "Entry Tap Detected: %s", card_uid);
            bool allowed = false;
            char msg[64] = {0};
            if (network_send_rfid_tap(GATE_ENTRY, card_uid, &allowed, msg, sizeof(msg)) == ESP_OK && allowed) {
                barrier_open(GATE_ENTRY);
            }
        }

        // Quét cổng ra
        if (rfid_reader_poll(GATE_EXIT, card_uid, sizeof(card_uid)) == ESP_OK) {
            ESP_LOGI(TAG, "Exit Tap Detected: %s", card_uid);
            bool allowed = false;
            char msg[64] = {0};
            if (network_send_rfid_tap(GATE_EXIT, card_uid, &allowed, msg, sizeof(msg)) == ESP_OK && allowed) {
                barrier_open(GATE_EXIT);
            }
        }

        vTaskDelay(pdMS_TO_TICKS(150));
    }
}

static void barrier_task(void *pvParameters) {
    ESP_LOGI(TAG, "Barrier safety monitor task started.");
    while (1) {
        // Tự động đóng barrier sau khi xe qua và không có vật cản
        for (int gate = 0; gate < 2; gate++) {
            if (barrier_get_state(gate) == BARRIER_OPEN) {
                if (!barrier_is_obstruction_detected(gate)) {
                    vTaskDelay(pdMS_TO_TICKS(3000)); // Đếm trễ an toàn 3 giây
                    barrier_close(gate);
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

static void network_task(void *pvParameters) {
    ESP_LOGI(TAG, "Network telemetry task started.");
    while (1) {
        network_send_telemetry(g_slots);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

// ==============================================================================
// ENTRY POINT
// ==============================================================================

void app_main(void) {
    ESP_LOGI(TAG, "================================================");
    ESP_LOGI(TAG, "SMART PARKING SYSTEM FIRMWARE INITIALIZING");
    ESP_LOGI(TAG, "Target: ESP32 | FreeRTOS Architecture");
    ESP_LOGI(TAG, "================================================");

    // 1. Khởi tạo phần cứng trừu tượng
    ultrasonic_sensor_init();
    rfid_reader_init();
    barrier_controller_init();
    display_lcd_init();
    network_client_init();

    display_lcd_show_status(4, "SYSTEM READY");

    // 2. Tạo các tác vụ FreeRTOS độc lập
    xTaskCreatePinnedToCore(sensor_task, "sensor_task", 4096, NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(rfid_task, "rfid_task", 4096, NULL, 6, NULL, 1);
    xTaskCreatePinnedToCore(barrier_task, "barrier_task", 3072, NULL, 4, NULL, 0);
    xTaskCreatePinnedToCore(network_task, "network_task", 4096, NULL, 3, NULL, 0);

    ESP_LOGI(TAG, "All FreeRTOS tasks launched successfully.");
}
