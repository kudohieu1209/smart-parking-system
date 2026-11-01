/**
 * @file network_client.h
 * @brief Giao diện kết nối Wi-Fi Station và HTTP REST Client cho ESP32.
 */

#ifndef NETWORK_CLIENT_H
#define NETWORK_CLIENT_H

#include <esp_err.h>
#include <stdbool.h>
#include <stddef.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Khởi tạo NVS, Wi-Fi Station và kết nối vào AP (Wokwi-GUEST trên giả lập hoặc cấu hình thật).
 */
esp_err_t network_client_init(void);

/**
 * @brief Kiểm tra trạng thái kết nối mạng Wi-Fi và IP.
 */
bool network_client_is_connected(void);

/**
 * @brief Gửi số liệu cảm biến siêu âm của 4 ô đỗ lên FastAPI Backend (/api/v1/telemetry/sensors).
 */
esp_err_t network_send_telemetry(const slot_telemetry_t slots[MAX_SLOTS]);

/**
 * @brief Gửi sự kiện quẹt thẻ RFID lên Backend và nhận quyết định mở cổng.
 * 
 * @param gate Cổng quẹt (GATE_ENTRY hoặc GATE_EXIT)
 * @param card_uid Mã thẻ (VD: "30A-123.45" hoặc "01:02:03:04")
 * @param out_allowed Nhận quyết định từ Backend: true nếu ALLOWED, false nếu REJECTED
 * @param out_msg Thông điệp phản hồi từ Backend
 * @param msg_len Kích thước buffer out_msg
 */
esp_err_t network_send_rfid_tap(gate_id_t gate, const char *card_uid, bool *out_allowed, char *out_msg, size_t msg_len);

#ifdef __cplusplus
}
#endif

#endif // NETWORK_CLIENT_H
