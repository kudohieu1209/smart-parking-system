/**
 * @file pin_config.h
 * @brief Định nghĩa chân GPIO tham chiếu dự kiến cho ESP32 DevKit V1.
 * 
 * LƯU Ý: Đây là cấu hình sơ bộ phục vụ kiến trúc trừu tượng hoá phần cứng (HAL).
 * Các chân có thể điều chỉnh qua Kconfig / menuconfig khi xác định bo mạch vật lý.
 */

#ifndef PIN_CONFIG_H
#define PIN_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

// ==============================================================================
// 1. CẢM BIẾN SIÊU ÂM (HC-SR04) CHO 4 Ô ĐỖ (P01 .. P04)
// ==============================================================================
#define PIN_ULTRASONIC_P01_TRIG    (12)
#define PIN_ULTRASONIC_P01_ECHO    (14)

#define PIN_ULTRASONIC_P02_TRIG    (27)
#define PIN_ULTRASONIC_P02_ECHO    (26)

#define PIN_ULTRASONIC_P03_TRIG    (25)
#define PIN_ULTRASONIC_P03_ECHO    (33)

#define PIN_ULTRASONIC_P04_TRIG    (32)
#define PIN_ULTRASONIC_P04_ECHO    (35)  // Chân 35 là input-only, rất phù hợp cho Echo

// ==============================================================================
// 2. ĐẦU ĐỌC THẺ RFID RC522 (GIAO TIẾP SPI BUS)
// ==============================================================================
#define PIN_RFID_SPI_SCK           (18)
#define PIN_RFID_SPI_MISO          (19)
#define PIN_RFID_SPI_MOSI          (23)
#define PIN_RFID_ENTRY_CS          (5)   // Chip Select cho đầu đọc vào
#define PIN_RFID_EXIT_CS           (4)   // Chip Select cho đầu đọc ra
#define PIN_RFID_RST               (17)  // Reset chân chung

// ==============================================================================
// 3. ĐIỀU KHIỂN SERVO BARRIER (PWM / LEDC)
// ==============================================================================
#define PIN_SERVO_BARRIER_ENTRY    (13)
#define PIN_SERVO_BARRIER_EXIT     (15)

// ==============================================================================
// 4. CẢM BIẾN AN TOÀN TRÁNH KẸT XE TẠI CỔNG (IR SENSOR)
// ==============================================================================
#define PIN_SAFETY_IR_ENTRY        (16)
#define PIN_SAFETY_IR_EXIT         (2)

// ==============================================================================
// 5. MÀN HÌNH LCD I2C HIỂN THỊ CỔNG (TÙY CHỌN)
// ==============================================================================
#define PIN_I2C_SDA                (21)
#define PIN_I2C_SCL                (22)

#ifdef __cplusplus
}
#endif

#endif // PIN_CONFIG_H
