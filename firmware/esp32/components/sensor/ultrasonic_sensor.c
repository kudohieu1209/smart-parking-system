/**
 * @file ultrasonic_sensor.c
 * @brief Driver cảm biến siêu âm HC-SR04 chuẩn công nghiệp cho ESP32.
 */

#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <esp_timer.h>
#include <esp_rom_sys.h>
#include <driver/gpio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "ultrasonic_sensor.h"
#include "pin_config.h"

static const char *TAG = "ULTRASONIC_SENSOR";

#define FILTER_WINDOW_SIZE 3
#define ECHO_TIMEOUT_US    30000 // 30ms timeout (~5.1 mét)

typedef struct {
    gpio_num_t trig_pin;
    gpio_num_t echo_pin;
} sensor_pins_t;

static const sensor_pins_t g_sensors[MAX_SLOTS] = {
    { (gpio_num_t)PIN_ULTRASONIC_P01_TRIG, (gpio_num_t)PIN_ULTRASONIC_P01_ECHO },
    { (gpio_num_t)PIN_ULTRASONIC_P02_TRIG, (gpio_num_t)PIN_ULTRASONIC_P02_ECHO },
    { (gpio_num_t)PIN_ULTRASONIC_P03_TRIG, (gpio_num_t)PIN_ULTRASONIC_P03_ECHO },
    { (gpio_num_t)PIN_ULTRASONIC_P04_TRIG, (gpio_num_t)PIN_ULTRASONIC_P04_ECHO },
};

// Bộ lọc trung bình trượt và trạng thái lưu giữ
static float g_filter_buffer[MAX_SLOTS][FILTER_WINDOW_SIZE];
static int g_filter_index[MAX_SLOTS] = {0};
static int g_filter_count[MAX_SLOTS] = {0};
static bool g_last_occupied[MAX_SLOTS] = {false, false, false, false};
static uint32_t g_error_counts[MAX_SLOTS] = {0};

esp_err_t ultrasonic_sensor_init(void) {
    ESP_LOGI(TAG, "Initializing 4x HC-SR04 Ultrasonic Sensors (Hardware Microsecond Timer)...");

    for (int i = 0; i < MAX_SLOTS; i++) {
        // Cấu hình chân Trigger (Output)
        gpio_reset_pin(g_sensors[i].trig_pin);
        gpio_set_direction(g_sensors[i].trig_pin, GPIO_MODE_OUTPUT);
        gpio_set_level(g_sensors[i].trig_pin, 0);

        // Cấu hình chân Echo (Input-only)
        gpio_reset_pin(g_sensors[i].echo_pin);
        gpio_set_direction(g_sensors[i].echo_pin, GPIO_MODE_INPUT);
        // Chân input-only (GPIO 34-39) không có internal pullup/pulldown, không cần gọi gpio_pullup_dis

        // Khởi tạo bộ đệm lọc
        g_filter_index[i] = 0;
        g_filter_count[i] = 0;
        g_last_occupied[i] = false;
        g_error_counts[i] = 0;
        for (int j = 0; j < FILTER_WINDOW_SIZE; j++) {
            g_filter_buffer[i][j] = 120.0f; // Khởi tạo ban đầu trống
        }
    }

    ESP_LOGI(TAG, "All 4 HC-SR04 pins configured (Trig=[25,26,27,32], Echo=[34,35,36,39]).");
    return ESP_OK;
}

uint32_t ultrasonic_sensor_get_error_count(int slot_index) {
    if (slot_index < 0 || slot_index >= MAX_SLOTS) return 0;
    return g_error_counts[slot_index];
}

esp_err_t ultrasonic_sensor_read_slot(int slot_index, float *out_distance_cm, bool *out_occupied) {
    if (slot_index < 0 || slot_index >= MAX_SLOTS || !out_distance_cm || !out_occupied) {
        return ESP_ERR_INVALID_ARG;
    }

    gpio_num_t trig = g_sensors[slot_index].trig_pin;
    gpio_num_t echo = g_sensors[slot_index].echo_pin;

    // 1. Phát xung Trigger 10µs chính xác
    gpio_set_level(trig, 0);
    esp_rom_delay_us(4);
    gpio_set_level(trig, 1);
    esp_rom_delay_us(10);
    gpio_set_level(trig, 0);

    // 2. Chờ chân Echo lên mức HIGH với hardware timer
    int64_t wait_start = esp_timer_get_time();
    while (gpio_get_level(echo) == 0) {
        if ((esp_timer_get_time() - wait_start) > ECHO_TIMEOUT_US) {
            g_error_counts[slot_index]++;
            if (g_error_counts[slot_index] >= 3) {
                ESP_LOGW(TAG, "P0%d: Echo timeout (%u consecutive errors). Retaining last state.",
                         slot_index + 1, (unsigned int)g_error_counts[slot_index]);
            }
            // Không gán nhầm thành ô trống khi lỗi! Giữ nguyên trạng thái cũ
            *out_occupied = g_last_occupied[slot_index];
            *out_distance_cm = g_filter_buffer[slot_index][g_filter_index[slot_index]];
            return ESP_ERR_TIMEOUT;
        }
    }

    // 3. Đo thời gian chân Echo giữ mức HIGH
    int64_t echo_start = esp_timer_get_time();
    while (gpio_get_level(echo) == 1) {
        if ((esp_timer_get_time() - echo_start) > ECHO_TIMEOUT_US) {
            break;
        }
    }
    int64_t echo_end = esp_timer_get_time();
    uint32_t pulse_duration_us = (uint32_t)(echo_end - echo_start);

    // Tính khoảng cách: d = (t * 0.0343) / 2 = t / 58.0f
    float raw_distance = (float)pulse_duration_us / 58.0f;
    if (raw_distance < 2.0f) raw_distance = 2.0f;
    if (raw_distance > 400.0f) raw_distance = 400.0f;

    // Thành công: Xóa biến đếm lỗi
    g_error_counts[slot_index] = 0;

    // 4. Lọc trung bình trượt 3 mẫu (Moving Average Filter)
    g_filter_buffer[slot_index][g_filter_index[slot_index]] = raw_distance;
    g_filter_index[slot_index] = (g_filter_index[slot_index] + 1) % FILTER_WINDOW_SIZE;
    if (g_filter_count[slot_index] < FILTER_WINDOW_SIZE) {
        g_filter_count[slot_index]++;
    }

    float sum = 0.0f;
    for (int i = 0; i < g_filter_count[slot_index]; i++) {
        sum += g_filter_buffer[slot_index][i];
    }
    float filtered_distance = sum / (float)g_filter_count[slot_index];

    // 5. Áp dụng Hysteresis (Vùng trễ chống rung ngưỡng 25cm ± 2cm)
    bool is_occupied = g_last_occupied[slot_index];
    if (filtered_distance <= (DISTANCE_THRESHOLD_OCCUPIED_CM - DISTANCE_HYSTERESIS_CM)) {
        is_occupied = true;  // < 23.0cm: Chắc chắn CÓ XE
    } else if (filtered_distance >= (DISTANCE_THRESHOLD_OCCUPIED_CM + DISTANCE_HYSTERESIS_CM)) {
        is_occupied = false; // > 27.0cm: Chắc chắn TRỐNG
    }
    // Nằm giữa 23cm và 27cm: Giữ nguyên trạng thái trước đó

    g_last_occupied[slot_index] = is_occupied;
    *out_distance_cm = filtered_distance;
    *out_occupied = is_occupied;

    return ESP_OK;
}

esp_err_t ultrasonic_sensor_read_all(slot_telemetry_t slots[MAX_SLOTS]) {
    for (int i = 0; i < MAX_SLOTS; i++) {
        snprintf(slots[i].slot_id, sizeof(slots[i].slot_id), "P0%d", i + 1);
        float dist = 0.0f;
        bool occ = false;
        esp_err_t ret = ultrasonic_sensor_read_slot(i, &dist, &occ);
        if (ret == ESP_OK) {
            slots[i].distance_cm = dist;
            slots[i].occupied = occ;
            slots[i].last_update_ms = (uint32_t)(esp_timer_get_time() / 1000);
        } else {
            // Khi lỗi, giữ nguyên trạng thái trước đó, không gán trống
            slots[i].occupied = g_last_occupied[i];
        }
        // Giãn cách 15ms giữa các ô đỗ để tránh phản xạ sóng âm chéo giữa các cảm biến cạnh nhau
        esp_rom_delay_us(15000);
    }
    return ESP_OK;
}
