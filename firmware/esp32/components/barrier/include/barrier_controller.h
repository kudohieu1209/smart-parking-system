/**
 * @file barrier_controller.h
 * @brief Điều khiển động cơ Servo cho Barrier cổng vào & cổng ra tích hợp cảm biến an toàn.
 */

#ifndef BARRIER_CONTROLLER_H
#define BARRIER_CONTROLLER_H

#include <esp_err.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t barrier_controller_init(void);
esp_err_t barrier_open(gate_id_t gate);
esp_err_t barrier_close(gate_id_t gate);
bool barrier_is_obstruction_detected(gate_id_t gate);
barrier_state_t barrier_get_state(gate_id_t gate);

#ifdef __cplusplus
}
#endif

#endif // BARRIER_CONTROLLER_H
