/**
 * @file barrier_controller.h
 * @brief Điều khiển động cơ Servo Barrier qua LEDC PWM và cảm biến quang an toàn.
 */

#ifndef BARRIER_CONTROLLER_H
#define BARRIER_CONTROLLER_H

#include <esp_err.h>
#include <stdbool.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Khởi tạo LEDC PWM 50Hz cho 2 servo (GPIO 13 & 14) và cảm biến quang an toàn (GPIO 33 & 16).
 */
esp_err_t barrier_controller_init(void);

/**
 * @brief Mở barrier đến góc 90 độ (PWM ~1.5ms).
 */
esp_err_t barrier_open(gate_id_t gate);

/**
 * @brief Hạ barrier về góc 0 độ (PWM ~0.5ms) có kiểm tra liên động an toàn.
 * 
 * @return esp_err_t:
 *         - ESP_OK: Hạ barrier thành công
 *         - ESP_ERR_INVALID_STATE: Từ chối hạ do phát hiện vật cản dưới cánh chắn
 */
esp_err_t barrier_close(gate_id_t gate);

/**
 * @brief Kiểm tra cảm biến quang xem có vật cản chắn ngang cánh tay barrier hay không.
 * @return true nếu có xe/người đứng dưới cánh chắn, false nếu thông thoáng.
 */
bool barrier_is_obstruction_detected(gate_id_t gate);

/**
 * @brief Lấy trạng thái hiện tại của barrier (BARRIER_OPEN hoặc BARRIER_CLOSED).
 */
barrier_state_t barrier_get_state(gate_id_t gate);

/**
 * @brief Lấy góc xoay hiện tại của servo (0 đến 90 độ).
 */
int barrier_get_angle(gate_id_t gate);

#ifdef __cplusplus
}
#endif

#endif // BARRIER_CONTROLLER_H
