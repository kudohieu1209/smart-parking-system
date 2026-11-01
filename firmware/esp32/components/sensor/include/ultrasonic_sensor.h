/**
 * @file ultrasonic_sensor.h
 * @brief Giao diện điều khiển cảm biến siêu âm HC-SR04 cho 4 ô đỗ.
 */

#ifndef ULTRASONIC_SENSOR_H
#define ULTRASONIC_SENSOR_H

#include <esp_err.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define DISTANCE_THRESHOLD_OCCUPIED_CM (30.0f)

esp_err_t ultrasonic_sensor_init(void);
esp_err_t ultrasonic_sensor_read_slot(int slot_index, float *out_distance_cm, bool *out_occupied);
esp_err_t ultrasonic_sensor_read_all(slot_telemetry_t slots[MAX_SLOTS]);

#ifdef __cplusplus
}
#endif

#endif // ULTRASONIC_SENSOR_H
