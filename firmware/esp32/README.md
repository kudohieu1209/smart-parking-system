# HƯỚNG DẪN BUILD VÀ NẠP FIRMWARE ESP32 — SMART PARKING SYSTEM

Tài liệu này hướng dẫn cách cấu hình, biên dịch và nạp mã nguồn nhúng ESP32 (ESP-IDF C + FreeRTOS) vào bo mạch phần cứng thực tế.

> [!NOTE]
> **Hiện trạng môi trường máy tính:** ESP-IDF (`idf.py`) hiện **chưa được cài đặt** trên hệ thống này.
> Theo quy tắc phát triển phần mềm an toàn, hệ thống không tự ý cài đặt bộ công cụ toàn cục. Khi bạn chuẩn bị phần cứng thực tế, hãy làm theo hướng dẫn dưới đây để thiết lập môi trường và build firmware.

---

## 1. Yêu cầu phần mềm & công cụ

- Bo mạch: **ESP32-WROOM-32 DevKit V1** (hoặc ESP32-S3).
- Bộ công cụ: **ESP-IDF v5.1** hoặc mới hơn.
- Cáp kết nối Micro-USB hoặc Type-C có hỗ trợ truyền dữ liệu.
- Driver USB-to-UART: CP210x hoặc CH340 tuỳ bo mạch.

### Cài đặt ESP-IDF trên Windows
1. Tải bộ cài tự động chính thức từ Espressif:  
   👉 [ESP-IDF Tools Installer (Windows)](https://dl.espressif.com/dl/esp-idf/)
2. Chạy file cài đặt, chọn phiên bản khuyến nghị **ESP-IDF v5.1.x** hoặc **v5.2.x**.
3. Sau khi cài đặt hoàn tất, mở cửa sổ terminal **ESP-IDF 5.x PowerShell** do bộ cài tạo trên Desktop/Start Menu.

---

## 2. Cấu hình phần cứng & Sơ đồ chân

Toàn bộ sơ đồ chân GPIO được định nghĩa tập trung tại:
`firmware/esp32/components/parking_core/include/pin_config.h`

Bạn có thể chỉnh sửa các định nghĩa sau để khớp với sơ đồ nối dây thực tế:
- Cảm biến siêu âm 4 ô đỗ: `PIN_ULTRASONIC_P01_TRIG`, `PIN_ULTRASONIC_P01_ECHO`, ...
- Đầu đọc RFID RC522: Chân SPI `SCK`, `MISO`, `MOSI`, `PIN_RFID_ENTRY_CS`, `PIN_RFID_EXIT_CS`.
- Động cơ Servo Barrier: `PIN_SERVO_BARRIER_ENTRY`, `PIN_SERVO_BARRIER_EXIT`.
- Cảm biến hồng ngoại an toàn: `PIN_SAFETY_IR_ENTRY`, `PIN_SAFETY_IR_EXIT`.

---

## 3. Quy trình Build & Flash (Biên dịch và Nạp)

Mở terminal **ESP-IDF PowerShell** và di chuyển vào thư mục firmware:

```powershell
cd D:\Vibe\Project\SMART-PARKING-SYSTEM\firmware\esp32
```

### Bước 1: Thiết lập chip đích
```powershell
idf.py set-target esp32
```

### Bước 2: Cấu hình hệ thống (Tùy chọn)
Mở menu cấu hình nếu muốn tinh chỉnh xung nhịp CPU, dung lượng Flash, hoặc thông tin Wi-Fi:
```powershell
idf.py menuconfig
```

### Bước 3: Biên dịch mã nguồn (Build)
```powershell
idf.py build
```
Quá trình build thành công sẽ tạo ra file `smart_parking_esp32.bin` trong thư mục `build/`.

### Bước 4: Nạp vào vi điều khiển và theo dõi Log (Flash & Monitor)
Thay thế `COM3` bằng cổng COM thực tế mà máy tính nhận diện:
```powershell
idf.py -p COM3 -b 115200 flash monitor
```
*(Bấm phím `Ctrl + ]` để thoát khỏi màn hình monitor khi hoàn tất).*

---

## 4. Kiến trúc Đa nhiệm FreeRTOS trong Firmware

Firmware chia việc xử lý thành 4 tác vụ độc lập chạy đồng thời trên 2 nhân CPU:
- **`sensor_task` (Core 1, Ưu tiên 5):** Quét tuần tự 4 cảm biến siêu âm mỗi 500ms.
- **`rfid_task` (Core 1, Ưu tiên 6):** Lắng nghe sự kiện quẹt thẻ vào/ra với độ trễ tối thiểu.
- **`barrier_task` (Core 0, Ưu tiên 4):** Kiểm tra cảm biến quang an toàn và điều khiển đóng mở barrier theo chu kỳ an toàn.
- **`network_task` (Core 0, Ưu tiên 3):** Đóng gói telemetry và truyền dữ liệu lên Backend qua HTTP/MQTT.
