/**
 * @file display_lcd.c
 * @brief Driver màn hình LCD 1602 qua chip mở rộng I2C PCF8574 cho ESP32 & Wokwi.
 */

#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <driver/i2c.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "display_lcd.h"
#include "pin_config.h"

static const char *TAG = "LCD1602_I2C";

#define I2C_MASTER_NUM              I2C_NUM_0
#define I2C_MASTER_FREQ_HZ          100000
#define I2C_MASTER_TX_BUF_DISABLE   0
#define I2C_MASTER_RX_BUF_DISABLE   0

#define LCD_BACKLIGHT_BIT           0x08
#define LCD_EN_BIT                  0x04
#define LCD_RS_BIT                  0x01

static uint8_t g_backlight = LCD_BACKLIGHT_BIT;

static esp_err_t pcf8574_write_byte(uint8_t data) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (LCD_I2C_ADDRESS << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(cmd);
    return ret;
}

static void lcd_pulse_enable(uint8_t nibble) {
    pcf8574_write_byte(nibble | LCD_EN_BIT | g_backlight);
    ets_delay_us(5);
    pcf8574_write_byte((nibble & ~LCD_EN_BIT) | g_backlight);
    ets_delay_us(50);
}

static void lcd_send_nibble(uint8_t nibble, uint8_t rs) {
    uint8_t data = (nibble & 0xF0) | (rs ? LCD_RS_BIT : 0);
    lcd_pulse_enable(data);
}

static void lcd_send_byte(uint8_t val, uint8_t rs) {
    lcd_send_nibble(val & 0xF0, rs);
    lcd_send_nibble((val << 4) & 0xF0, rs);
}

static void lcd_send_cmd(uint8_t cmd) {
    lcd_send_byte(cmd, 0);
    if (cmd == 0x01 || cmd == 0x02) {
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

static void lcd_send_data(uint8_t data) {
    lcd_send_byte(data, 1);
}

static void lcd_set_cursor(uint8_t row, uint8_t col) {
    uint8_t addr = (row == 0) ? 0x80 + col : 0xC0 + col;
    lcd_send_cmd(addr);
}

static void lcd_write_string(const char *str) {
    while (*str) {
        lcd_send_data((uint8_t)(*str));
        str++;
    }
}

esp_err_t display_lcd_init(void) {
    ESP_LOGI(TAG, "Initializing LCD 1602 I2C (SDA=GPIO%d, SCL=GPIO%d, Addr=0x%02X)...",
             PIN_I2C_SDA, PIN_I2C_SCL, LCD_I2C_ADDRESS);

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = PIN_I2C_SCL,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ
    };
    esp_err_t ret = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (ret != ESP_OK) return ret;

    ret = i2c_driver_install(I2C_MASTER_NUM, conf.mode,
                             I2C_MASTER_RX_BUF_DISABLE,
                             I2C_MASTER_TX_BUF_DISABLE, 0);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) return ret;

    // Chuỗi khởi tạo HD44780 chế độ 4-bit qua PCF8574
    vTaskDelay(pdMS_TO_TICKS(50));
    lcd_send_nibble(0x30, 0);
    vTaskDelay(pdMS_TO_TICKS(5));
    lcd_send_nibble(0x30, 0);
    ets_delay_us(150);
    lcd_send_nibble(0x30, 0);
    ets_delay_us(150);
    lcd_send_nibble(0x20, 0); // Đặt chế độ 4-bit
    ets_delay_us(150);

    lcd_send_cmd(0x28); // 2 dòng, font 5x8
    lcd_send_cmd(0x0C); // Bật hiển thị, tắt con trỏ
    lcd_send_cmd(0x06); // Tự động tăng con trỏ
    lcd_send_cmd(0x01); // Xóa màn hình

    ESP_LOGI(TAG, "LCD 1602 initialized successfully.");
    return ESP_OK;
}

esp_err_t display_lcd_show_status(int available_slots, const char *message) {
    char line1[17];
    char line2[17];

    snprintf(line1, sizeof(line1), "SLOTS: %d/4 FREE ", available_slots);
    snprintf(line2, sizeof(line2), "%-16s", message ? message : "SYSTEM READY");

    lcd_set_cursor(0, 0);
    lcd_write_string(line1);

    lcd_set_cursor(1, 0);
    lcd_write_string(line2);

    return ESP_OK;
}
