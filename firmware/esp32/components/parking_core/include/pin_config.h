/**
 * @file pin_config.h
 * @brief Định nghĩa chân GPIO hoàn chỉnh cho ESP32 DevKit V1 / V4 trên mô phỏng Wokwi & phần cứng thật.
 * 
 * THIẾT KẾ AN TOÀN KHÔNG XUNG ĐỘT (STRAPPING-SAFE):
 * - Không sử dụng GPIO 12 (MTDI strapping - tránh lỗi flash voltage 1.8V/3.3V).
 * - Không sử dụng GPIO 15 (MTDO strapping - tránh nhiễu PWM lúc boot làm giật servo).
 * - Không sử dụng GPIO 0, 2 (Boot strapping & download mode).
 * - Không sử dụng GPIO 6-11 (Giao tiếp SPI Flash nội bộ).
 * - 4 chân Echo sử dụng đúng các chân Input-Only (GPIO 34, 35, 36/VP, 39/VN) - tối ưu phần cứng ESP32.
 */

#ifndef PIN_CONFIG_H
#define PIN_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

// ==============================================================================
// 1. CẢM BIẾN SIÊU ÂM (HC-SR04) CHO 4 Ô ĐỖ (P01 .. P04)
// ==============================================================================
// P01
#define PIN_ULTRASONIC_P01_TRIG    (25)
#define PIN_ULTRASONIC_P01_ECHO    (34)  // Input-only, an toàn tuyệt đối

// P02
#define PIN_ULTRASONIC_P02_TRIG    (26)
#define PIN_ULTRASONIC_P02_ECHO    (35)  // Input-only

// P03
#define PIN_ULTRASONIC_P03_TRIG    (27)
#define PIN_ULTRASONIC_P03_ECHO    (36)  // SENSOR_VP / GPIO36 (Input-only)

// P04
#define PIN_ULTRASONIC_P04_TRIG    (32)
#define PIN_ULTRASONIC_P04_ECHO    (39)  // SENSOR_VN / GPIO39 (Input-only)

#define DISTANCE_THRESHOLD_OCCUPIED_CM  (25.0f)
#define DISTANCE_HYSTERESIS_CM          (2.0f)  // Hysteresis: <23cm Có xe, >27cm Trống

// ==============================================================================
// 2. ĐẦU ĐỌC THẺ RFID RC522 (GIAO TIẾP SPI BUS - VSPI)
// ==============================================================================
#define PIN_RFID_SPI_SCK           (18)
#define PIN_RFID_SPI_MISO          (19)
#define PIN_RFID_SPI_MOSI          (23)
#define PIN_RFID_ENTRY_CS          (5)   // Chip Select cổng vào
#define PIN_RFID_EXIT_CS           (4)   // Chip Select cổng ra
#define PIN_RFID_RST               (17)  // Chân Reset chung cho RC522

// ==============================================================================
// 3. ĐIỀU KHIỂN SERVO BARRIER (LEDC PWM 50Hz)
// ==============================================================================
#define PIN_SERVO_BARRIER_ENTRY    (13)
#define PIN_SERVO_BARRIER_EXIT     (14)  // Tránh GPIO 15 boot noise

// ==============================================================================
// 4. CẢM BIẾN AN TOÀN QUANG TRÁNH KẸT XE TẠI CỔNG (IR / PHOTOELECTRIC BEAM)
// ==============================================================================
#define PIN_SAFETY_IR_ENTRY        (33)  // Cảm biến quang Cổng Vào (Active LOW)
#define PIN_SAFETY_IR_EXIT         (16)  // Cảm biến quang Cổng Ra (Active LOW)

// ==============================================================================
// 5. MÀN HÌNH LCD 1602 I2C (PCF8574T ADAPTER)
// ==============================================================================
#define PIN_I2C_SDA                (21)
#define PIN_I2C_SCL                (22)
#define LCD_I2C_ADDRESS            (0x27) // Địa chỉ PCF8574 mặc định trong Wokwi

// ==============================================================================
// 6. CẤU HÌNH MẠNG WI-FI & BACKEND
// ==============================================================================
#ifdef CONFIG_SMART_PARKING_WIFI_SSID
#define WIFI_SSID_DEFAULT          CONFIG_SMART_PARKING_WIFI_SSID
#else
#define WIFI_SSID_DEFAULT          "Wokwi-GUEST"  // Mạng Wi-Fi ảo của Wokwi Simulator
#endif

#ifdef CONFIG_SMART_PARKING_WIFI_PASSWORD
#define WIFI_PASS_DEFAULT          CONFIG_SMART_PARKING_WIFI_PASSWORD
#else
#define WIFI_PASS_DEFAULT          ""
#endif

#ifdef CONFIG_SMART_PARKING_BACKEND_URL
#define BACKEND_BASE_URL_DEFAULT   CONFIG_SMART_PARKING_BACKEND_URL
#else
#define BACKEND_BASE_URL_DEFAULT   "http://10.0.2.2:8000/api/v1" // Host gateway trong mạng ảo Wokwi (10.0.2.2 trỏ về localhost máy tính)
#endif

#ifdef __cplusplus
}
#endif

#endif // PIN_CONFIG_H
