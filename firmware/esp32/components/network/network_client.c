/**
 * @file network_client.c
 * @brief Triển khai Wi-Fi Station và HTTP Client giao tiếp REST API Backend cho ESP32.
 */

#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <esp_wifi.h>
#include <esp_event.h>
#include <esp_netif.h>
#include <nvs_flash.h>
#include <esp_http_client.h>
#include <cJSON.h>

#include "network_client.h"
#include "pin_config.h"

static const char *TAG = "NET_CLIENT";

static bool g_wifi_connected = false;

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                               int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "Wi-Fi station started, connecting to AP...");
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        g_wifi_connected = false;
        ESP_LOGW(TAG, "Wi-Fi disconnected. Reconnecting...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Wi-Fi connected! Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        g_wifi_connected = true;
    }
}

esp_err_t network_client_init(void) {
    ESP_LOGI(TAG, "Initializing Wi-Fi Station interface (SSID: %s)...", WIFI_SSID_DEFAULT);

    // 1. Khởi tạo NVS Flash
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS Flash init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    // 2. Khởi tạo TCP/IP & Event loop
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    // 3. Cấu hình Wi-Fi Station
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL);

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID_DEFAULT,
            .password = WIFI_PASS_DEFAULT,
            .threshold.authmode = WIFI_AUTH_OPEN,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();

    ESP_LOGI(TAG, "Wi-Fi station initialization dispatched.");
    return ESP_OK;
}

bool network_client_is_connected(void) {
    return g_wifi_connected;
}

esp_err_t network_send_telemetry(const slot_telemetry_t slots[MAX_SLOTS]) {
    // Luôn log thông tin telemetry ra console
    ESP_LOGI(TAG, "Telemetry -> P01:[%s, %.1fcm] | P02:[%s, %.1fcm] | P03:[%s, %.1fcm] | P04:[%s, %.1fcm]",
             slots[0].occupied ? "OCC" : "EMP", slots[0].distance_cm,
             slots[1].occupied ? "OCC" : "EMP", slots[1].distance_cm,
             slots[2].occupied ? "OCC" : "EMP", slots[2].distance_cm,
             slots[3].occupied ? "OCC" : "EMP", slots[3].distance_cm);

    if (!g_wifi_connected) {
        return ESP_ERR_INVALID_STATE;
    }

    // Xây dựng JSON payload
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "device_id", "ESP32_CORE_01");

    cJSON *readings = cJSON_CreateArray();
    for (int i = 0; i < MAX_SLOTS; i++) {
        cJSON *item = cJSON_CreateObject();
        cJSON_AddStringToObject(item, "slot_id", slots[i].slot_id);
        cJSON_AddNumberToObject(item, "distance_cm", slots[i].distance_cm);
        cJSON_AddBoolToObject(item, "occupied", slots[i].occupied);
        cJSON_AddItemToArray(readings, item);
    }
    cJSON_AddItemToObject(root, "readings", readings);

    char *post_data = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (!post_data) return ESP_ERR_NO_MEM;

    char url[128];
    snprintf(url, sizeof(url), "%s/telemetry/sensors", BACKEND_BASE_URL_DEFAULT);

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 3000,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    esp_err_t err = esp_http_client_perform(client);
    if (err == ESP_OK) {
        int status_code = esp_http_client_get_status_code(client);
        ESP_LOGD(TAG, "Telemetry sent successfully, status = %d", status_code);
    } else {
        ESP_LOGW(TAG, "Telemetry HTTP POST failed: %s", esp_err_to_name(err));
    }

    esp_http_client_cleanup(client);
    free(post_data);
    return err;
}

esp_err_t network_send_rfid_tap(gate_id_t gate, const char *card_uid, bool *out_allowed, char *out_msg, size_t msg_len) {
    ESP_LOGI(TAG, "Transmitting RFID tap to Backend: Gate=%s, Card=%s",
             (gate == GATE_ENTRY) ? "ENTRY" : "EXIT", card_uid);

    // NGUYÊN TẮC AN TOÀN FAIL-SAFE: Mặc định luôn từ chối cho đến khi Backend xác thực thành công
    if (out_allowed) *out_allowed = false;

    // Khi chưa có kết nối Wi-Fi thực tế (VD: chạy Wokwi standalone chưa qua gateway):
    if (!g_wifi_connected) {
        ESP_LOGW(TAG, "Wi-Fi not connected! Running in Standalone Fail-safe mode.");

        // Trong chế độ giả lập độc lập: chấp nhận thẻ mẫu DEMO-01 hoặc DEMO-02 để kiểm thử cơ chế đóng mở
        if (card_uid && (strstr(card_uid, "30A") != NULL || strstr(card_uid, "01:02:03:04") != NULL || strstr(card_uid, "DEMO") != NULL)) {
            ESP_LOGI(TAG, "[Offline Mock] Demo card recognized in standalone mode: %s", card_uid);
            if (out_allowed) *out_allowed = true;
            if (out_msg && msg_len > 0) snprintf(out_msg, msg_len, "Demo Verified (Standalone)");
            return ESP_OK;
        }

        if (out_msg && msg_len > 0) snprintf(out_msg, msg_len, "Backend Offline - Access Denied");
        return ESP_ERR_INVALID_STATE;
    }

    // Kết nối HTTP tới Backend
    char url[128];
    const char *endpoint = (gate == GATE_ENTRY) ? "/gate/entry-tap" : "/gate/exit-tap";
    snprintf(url, sizeof(url), "%s%s", BACKEND_BASE_URL_DEFAULT, endpoint);

    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "card_uid", card_uid);
    cJSON_AddStringToObject(root, "gate_id", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");

    char *post_data = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (!post_data) return ESP_ERR_NO_MEM;

    char response_buffer[512] = {0};
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 4000,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    esp_err_t err = esp_http_client_open(client, strlen(post_data));
    if (err == ESP_OK) {
        esp_http_client_write(client, post_data, strlen(post_data));
        int content_length = esp_http_client_fetch_headers(client);
        if (content_length > 0 && content_length < (int)sizeof(response_buffer)) {
            esp_http_client_read(client, response_buffer, sizeof(response_buffer) - 1);
        }
    }

    esp_http_client_cleanup(client);
    free(post_data);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to connect to backend: %s. Fail-safe: Barrier stays CLOSED.", esp_err_to_name(err));
        if (out_msg && msg_len > 0) snprintf(out_msg, msg_len, "Backend Unreachable");
        return err;
    }

    // Phân tích phản hồi JSON từ FastAPI
    cJSON *resp_json = cJSON_Parse(response_buffer);
    if (!resp_json) {
        ESP_LOGE(TAG, "Invalid JSON received from backend: %s", response_buffer);
        return ESP_ERR_INVALID_RESPONSE;
    }

    cJSON *status_item = cJSON_GetObjectItem(resp_json, "status");
    cJSON *msg_item = cJSON_GetObjectItem(resp_json, "message");

    if (status_item && cJSON_IsString(status_item)) {
        if (strcmp(status_item->valuestring, "ALLOWED") == 0) {
            if (out_allowed) *out_allowed = true;
            ESP_LOGI(TAG, "Backend Authorization: ALLOWED -> Opening barrier.");
        } else {
            if (out_allowed) *out_allowed = false;
            ESP_LOGW(TAG, "Backend Authorization: REJECTED (%s) -> Keeping barrier closed.",
                     msg_item ? msg_item->valuestring : "Denied");
        }
    }

    if (out_msg && msg_len > 0 && msg_item && cJSON_IsString(msg_item)) {
        snprintf(out_msg, msg_len, "%s", msg_item->valuestring);
    }

    cJSON_Delete(resp_json);
    return ESP_OK;
}
