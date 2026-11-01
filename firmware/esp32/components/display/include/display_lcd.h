/**
 * @file display_lcd.h
 * @brief Giao diện hiển thị LCD 1602 / 2004 qua I2C.
 */

#ifndef DISPLAY_LCD_H
#define DISPLAY_LCD_H

#include <esp_err.h>

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t display_lcd_init(void);
esp_err_t display_lcd_show_status(int available_slots, const char *message);

#ifdef __cplusplus
}
#endif

#endif // DISPLAY_LCD_H
