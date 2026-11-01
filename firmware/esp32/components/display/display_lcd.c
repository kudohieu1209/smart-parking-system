#include <stdio.h>
#include <esp_log.h>
#include "display_lcd.h"
#include "pin_config.h"

static const char *TAG = "DISPLAY_LCD";

esp_err_t display_lcd_init(void) {
    ESP_LOGI(TAG, "Initializing LCD 1602 I2C Display (SDA: %d, SCL: %d)...", PIN_I2C_SDA, PIN_I2C_SCL);
    return ESP_OK;
}

esp_err_t display_lcd_show_status(int available_slots, const char *message) {
    ESP_LOGI(TAG, "LCD Update -> Available: %d/4 | Msg: %s", available_slots, message ? message : "");
    return ESP_OK;
}
