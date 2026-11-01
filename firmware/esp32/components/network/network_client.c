#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include "network_client.h"

static const char *TAG = "NETWORK_CLIENT";

esp_err_t network_client_init(void) {
    ESP_LOGI(TAG, "Initializing Network Client interface (Wi-Fi / HTTP / MQTT)...");
    return ESP_OK;
}

esp_err_t network_send_telemetry(const slot_telemetry_t slots[MAX_SLOTS]) {
    ESP_LOGI(TAG, "Transmitting slot telemetry: P01=%s, P02=%s, P03=%s, P04=%s",
             slots[0].occupied ? "OCCUPIED" : "EMPTY",
             slots[1].occupied ? "OCCUPIED" : "EMPTY",
             slots[2].occupied ? "OCCUPIED" : "EMPTY",
             slots[3].occupied ? "OCCUPIED" : "EMPTY");
    return ESP_OK;
}

esp_err_t network_send_rfid_tap(gate_id_t gate, const char *card_uid, bool *out_allowed, char *out_msg, size_t msg_len) {
    ESP_LOGI(TAG, "Transmitting RFID tap for gate %d, Card: %s", gate, card_uid);
    if (out_allowed) *out_allowed = true;
    if (out_msg && msg_len > 0) {
        snprintf(out_msg, msg_len, "Card verified");
    }
    return ESP_OK;
}
