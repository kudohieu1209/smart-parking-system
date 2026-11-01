/**
 * @file network_client.h
 * @brief Giao diện kết nối Wi-Fi và đẩy dữ liệu Telemetry / RFID Event lên Backend qua HTTP/MQTT.
 */

#ifndef NETWORK_CLIENT_H
#define NETWORK_CLIENT_H

#include <esp_err.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t network_client_init(void);
esp_err_t network_send_telemetry(const slot_telemetry_t slots[MAX_SLOTS]);
esp_err_t network_send_rfid_tap(gate_id_t gate, const char *card_uid, bool *out_allowed, char *out_msg, size_t msg_len);

#ifdef __cplusplus
}
#endif

#endif // NETWORK_CLIENT_H
