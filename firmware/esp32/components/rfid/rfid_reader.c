#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <driver/spi_master.h>
#include <driver/gpio.h>
#include "rfid_reader.h"
#include "pin_config.h"

static const char *TAG = "RFID_READER";

esp_err_t rfid_reader_init(void) {
    ESP_LOGI(TAG, "Initializing RC522 RFID SPI bus (SCK=%d, MISO=%d, MOSI=%d)...",
             PIN_RFID_SPI_SCK, PIN_RFID_SPI_MISO, PIN_RFID_SPI_MOSI);

    // Cấu hình chân CS cho Entry & Exit
    gpio_reset_pin(PIN_RFID_ENTRY_CS);
    gpio_set_direction(PIN_RFID_ENTRY_CS, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_RFID_ENTRY_CS, 1);

    gpio_reset_pin(PIN_RFID_EXIT_CS);
    gpio_set_direction(PIN_RFID_EXIT_CS, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_RFID_EXIT_CS, 1);

    ESP_LOGI(TAG, "RC522 RFID interfaces initialized successfully.");
    return ESP_OK;
}

esp_err_t rfid_reader_poll(gate_id_t gate, char *out_card_uid, size_t max_len) {
    if (!out_card_uid || max_len < 16) {
        return ESP_ERR_INVALID_ARG;
    }
    // Stub mô phỏng nhận thẻ khi kết nối phần cứng SPI thật
    // Khi tích hợp thư viện RC522 (PCD), hàm này đọc thanh ghi FIFO và giải mã 4-byte / 7-byte UID.
    return ESP_ERR_NOT_FOUND;
}
