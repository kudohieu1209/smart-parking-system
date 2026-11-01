/**
 * @file ultrasonic_sensor.h
 * @brief Giao diện điều khiển cảm biến siêu âm HC-SR04 cho 4 ô đỗ xe (ESP-IDF / Wokwi).
 * 
 * Tính năng:
 * - Đo chính xác độ rộng xung Echo bằng hardware microsecond timer (esp_timer_get_time).
 * - Lọc nhiễu trung bình trượt 3 mẫu (Moving Average).
 * - Vùng trễ chống rung dao động (Hysteresis Band).
 * - Xử lý timeout/mất tín hiệu (không gán nhầm thành ô trống khi cảm biến lỗi).
 */

#ifndef ULTRASONIC_SENSOR_H
#define ULTRASONIC_SENSOR_H

#include <esp_err.h>
#include "parking_types.h"
#include "pin_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Khởi tạo GPIO cho 4 cảm biến siêu âm HC-SR04.
 */
esp_err_t ultrasonic_sensor_init(void);

/**
 * @brief Đo khoảng cách thực tế của 1 ô đỗ.
 * 
 * @param slot_index Chỉ số ô (0 đến 3)
 * @param out_distance_cm Khoảng cách đo được (cm)
 * @param out_occupied Trạng thái có xe (áp dụng hysteresis)
 * @return esp_err_t ESP_OK nếu đọc thành công, ESP_ERR_TIMEOUT nếu mất xung phản hồi
 */
esp_err_t ultrasonic_sensor_read_slot(int slot_index, float *out_distance_cm, bool *out_occupied);

/**
 * @brief Đọc tuần tự toàn bộ 4 ô đỗ, áp dụng khoảng giãn cách 15ms chống phản xạ chéo.
 * 
 * @param slots Mảng telemetry 4 ô đỗ
 * @return esp_err_t ESP_OK
 */
esp_err_t ultrasonic_sensor_read_all(slot_telemetry_t slots[MAX_SLOTS]);

/**
 * @brief Lấy số lần lỗi timeout liên tiếp của một ô.
 */
uint32_t ultrasonic_sensor_get_error_count(int slot_index);

#ifdef __cplusplus
}
#endif

#endif // ULTRASONIC_SENSOR_H
