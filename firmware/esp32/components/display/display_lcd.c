/**
 * @file display_lcd.c
 * @brief Driver màn hình LCD 1602 qua chip mở rộng I2C PCF8574 cho ESP32 & Wokwi.
 * Chuẩn hóa hoàn toàn theo driver driver/i2c_master.h của ESP-IDF v5.x.
 */

#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <driver/i2c_master.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_rom_sys.h>

#include "display_lcd.h"
#include "pin_config.h"

static const char *TAG = "LCD1602_I2C";

#define I2C_MASTER_FREQ_HZ          100000

#define LCD_BACKLIGHT_BIT           0x08
#define LCD_EN_BIT                  0x04
#define LCD_RS_BIT                  0x01

static uint8_t g_backlight = LCD_BACKLIGHT_BIT;
static i2c_master_bus_handle_t s_i2c_bus = NULL;
static i2c_master_dev_handle_t s_lcd_dev = NULL;

static esp_err_t pcf8574_write_byte(uint8_t data) {
    if (!s_lcd_dev) return ESP_ERR_INVALID_STATE;
    return i2c_master_transmit(s_lcd_dev, &data, 1, 50);
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

    i2c_master_bus_config_t bus_config = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = (gpio_num_t)PIN_I2C_SDA,
        .scl_io_num = (gpio_num_t)PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    esp_err_t ret = i2c_new_master_bus(&bus_config, &s_i2c_bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create I2C master bus: %s", esp_err_to_name(ret));
        return ret;
    }

    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = LCD_I2C_ADDRESS,
        .scl_speed_hz = I2C_MASTER_FREQ_HZ,
    };
    ret = i2c_master_bus_add_device(s_i2c_bus, &dev_config, &s_lcd_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to attach LCD device: %s", esp_err_to_name(ret));
        return ret;
    }

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
    vTaskDelay(pdMS_TO_TICKS(5));

    ESP_LOGI(TAG, "LCD 1602 initialized successfully via ESP-IDF v5.x i2c_master driver.");
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
