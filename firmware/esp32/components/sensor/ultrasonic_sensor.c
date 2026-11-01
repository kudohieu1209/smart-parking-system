#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <rom/ets_sys.h>
#include <driver/gpio.h>
#include "ultrasonic_sensor.h"
#include "pin_config.h"

static const char *TAG = "ULTRASONIC_SENSOR";

typedef struct {
    gpio_num_t trig_pin;
    gpio_num_t echo_pin;
} sensor_pins_t;

static const sensor_pins_t g_sensors[MAX_SLOTS] = {
    { PIN_ULTRASONIC_P01_TRIG, PIN_ULTRASONIC_P01_ECHO },
    { PIN_ULTRASONIC_P02_TRIG, PIN_ULTRASONIC_P02_ECHO },
    { PIN_ULTRASONIC_P03_TRIG, PIN_ULTRASONIC_P03_ECHO },
    { PIN_ULTRASONIC_P04_TRIG, PIN_ULTRASONIC_P04_ECHO },
};

esp_err_t ultrasonic_sensor_init(void) {
    ESP_LOGI(TAG, "Initializing 4x HC-SR04 ultrasonic sensors...");

    for (int i = 0; i < MAX_SLOTS; i++) {
        gpio_reset_pin(g_sensors[i].trig_pin);
        gpio_set_direction(g_sensors[i].trig_pin, GPIO_MODE_OUTPUT);
        gpio_set_level(g_sensors[i].trig_pin, 0);

        gpio_reset_pin(g_sensors[i].echo_pin);
        gpio_set_direction(g_sensors[i].echo_pin, GPIO_MODE_INPUT);
        gpio_pullup_dis(g_sensors[i].echo_pin);
    }

    ESP_LOGI(TAG, "Ultrasonic GPIO initialization completed.");
    return ESP_OK;
}

esp_err_t ultrasonic_sensor_read_slot(int slot_index, float *out_distance_cm, bool *out_occupied) {
    if (slot_index < 0 || slot_index >= MAX_SLOTS || !out_distance_cm || !out_occupied) {
        return ESP_ERR_INVALID_ARG;
    }

    gpio_num_t trig = g_sensors[slot_index].trig_pin;
    gpio_num_t echo = g_sensors[slot_index].echo_pin;

    // Phát xung trigger 10us
    gpio_set_level(trig, 0);
    ets_delay_us(2);
    gpio_set_level(trig, 1);
    ets_delay_us(10);
    gpio_set_level(trig, 0);

    // Chờ Echo lên cao (timeout 30ms)
    uint32_t timeout_us = 30000;
    while (gpio_get_level(echo) == 0 && timeout_us > 0) {
        ets_delay_us(1);
        timeout_us--;
    }
    if (timeout_us == 0) {
        *out_distance_cm = 400.0f; // No echo
        *out_occupied = false;
        return ESP_ERR_TIMEOUT;
    }

    // Đo độ rộng xung Echo
    uint32_t pulse_width_us = 0;
    while (gpio_get_level(echo) == 1 && pulse_width_us < 30000) {
        ets_delay_us(1);
        pulse_width_us++;
    }

    // Khoảng cách (cm) = thời gian (us) / 58
    float distance = (float)pulse_width_us / 58.0f;
    *out_distance_cm = distance;
    *out_occupied = (distance < DISTANCE_THRESHOLD_OCCUPIED_CM);

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
        } else {
            slots[i].distance_cm = 120.0f;
            slots[i].occupied = false;
        }
    }
    return ESP_OK;
}
