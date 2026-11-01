idf_component_register(
    SRCS "network_client.c"
    INCLUDE_DIRS "include"
    REQUIRES "parking_core" "esp_wifi" "esp_event" "nvs_flash" "esp_http_client" "json" "esp_netif"
)
