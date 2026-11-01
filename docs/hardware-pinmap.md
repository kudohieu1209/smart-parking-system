# SƠ ĐỒ CHÂN DỰ KIẾN & GIAO TIẾP PHẦN CỨNG — HARDWARE PINMAP (PRELIMINARY)

> [!IMPORTANT]
> **Lưu ý theo quy tắc thiết kế:** Đây là **sơ đồ chân tham chiếu dự kiến** dành cho bo mạch ESP32-WROOM-32 DevKit V1 khi phát triển mô hình lab. Sơ đồ chân cuối cùng chưa được cố định và sẽ được cấu hình linh hoạt thông qua file cấu hình `firmware/esp32/components/parking_core/include/pin_config.h` hoặc ESP-IDF `Kconfig` (menuconfig) khi xác định phần cứng thực tế.

---

## 1. Danh sách thiết bị phần cứng dự kiến

1. **Bộ vi điều khiển trung tâm:** ESP32 DevKit V1 (30 pins hoặc 38 pins).
2. **Cảm biến đỗ xe (4 vị trí P01 - P04):**
   - 4 cảm biến siêu âm HC-SR04 (hoặc module tương đương 3.3V/5V với điện trở phân áp echo).
3. **Đầu đọc thẻ RFID:**
   - 2 module RFID-RC522 (Giao tiếp SPI bus chung, tách chân Chip Select CS/SDA).
4. **Cơ cấu chấp hành Barrier:**
   - 2 Động cơ Servo SG90 hoặc MG996R (Điều khiển xung PWM).
5. **Cảm biến an toàn tại cổng (Safety IR Obstacle):**
   - 2 cảm biến quang/hồng ngoại phát hiện xe đang đứng chắn barie.
6. **Màn hình hiển thị trạng thái tại cổng (Tùy chọn):**
   - 1 màn hình I2C LCD 1602 hoặc 2004 (Địa chỉ 0x27).

---

## 2. Bảng phân bổ chân dự kiến (ESP32 Pinout Mapping)

### 2.1. Cảm biến siêu âm (HC-SR04) — 4 Ô đỗ P01..P04
| Ô đỗ | Chân Trigger (ESP32 Output) | Chân Echo (ESP32 Input qua phân áp) | Ghi chú |
| :--- | :--- | :--- | :--- |
| **P01** | GPIO 12 | GPIO 14 | Có thể chia sẻ chân Trigger nếu kích hoạt tuần tự |
| **P02** | GPIO 27 | GPIO 26 | Cần cầu chia áp cho Echo (5V -> 3.3V) |
| **P03** | GPIO 25 | GPIO 33 | Đọc xung bằng ngắt GPIO hoặc FreeRTOS RMT/Timer |
| **P04** | GPIO 32 | GPIO 35 (Input Only) | GPIO 35 chỉ nhận input, rất phù hợp cho Echo |

### 2.2. Giao tiếp RFID-RC522 (Cổng vào & Cổng ra) — SPI Bus
| Tín hiệu RC522 | Cổng Vào (Entry RC522) | Cổng Ra (Exit RC522) | Chân ESP32 | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **SCK** | SCK | SCK | GPIO 18 | SPI Clock chung |
| **MISO** | MISO | MISO | GPIO 19 | SPI MISO chung |
| **MOSI** | MOSI | MOSI | GPIO 23 | SPI MOSI chung |
| **SDA / SS (CS)**| SDA | - | GPIO 5 | Chip Select Đầu vào |
| **SDA / SS (CS)**| - | SDA | GPIO 4 | Chip Select Đầu ra |
| **RST** | RST | RST | GPIO 17 | Reset chung (hoặc tách riêng) |

### 2.3. Điều khiển Servo Barrier — PWM Output
| Thiết bị | Chân ESP32 | Kênh LEDC / Timer | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Servo Barrier Cổng Vào** | GPIO 13 | LEDC Channel 0, 50Hz | Góc 0° = Đóng, 90° = Mở |
| **Servo Barrier Cổng Ra** | GPIO 15 | LEDC Channel 1, 50Hz | Góc 0° = Đóng, 90° = Mở |

### 2.4. Cảm biến an toàn cổng vào/ra (IR Beam / Safety Sensor)
| Cảm biến | Chân ESP32 | Kiểu tín hiệu |
| :--- | :--- | :--- |
| **Safety IR Cổng Vào** | GPIO 16 | Digital Input (PULL-UP, 0: Có vật cản) |
| **Safety IR Cổng Ra** | GPIO 2 | Digital Input (PULL-UP, 0: Có vật cản) |

### 2.5. Màn hình I2C LCD (Hiển thị tại cổng)
| Tín hiệu I2C | Chân ESP32 | Ghi chú |
| :--- | :--- | :--- |
| **SDA** | GPIO 21 | Chuẩn I2C mặc định của ESP32 |
| **SCL** | GPIO 22 | Chuẩn I2C mặc định của ESP32 |

---

## 3. Hardware Abstraction Layer (HAL) trong Firmware

Để đảm bảo code firmware độc lập với việc thay đổi chân cắm vật lý sau này, toàn bộ định nghĩa chân được cô lập tại:
`firmware/esp32/components/parking_core/include/pin_config.h`

Mọi module thành phần (`sensor`, `rfid`, `barrier`) chỉ gọi thông qua các hàm trừu tượng hoá:
- `sensor_ultrasonic_read(slot_id, &distance_cm)`
- `barrier_open(gate_id)`
- `barrier_close(gate_id)`
- `rfid_poll_card(&gate_id, &card_uid)`
