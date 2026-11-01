# HƯỚNG DẪN MÔ PHỎNG PHẦN CỨNG WOKWI (WOKWI HARDWARE SETUP GUIDE)
## SMART PARKING SYSTEM — GIAI ĐOẠN 3: ESP32 + FREERTOS + WOKWI SIMULATION

Tài liệu này cung cấp sơ đồ kết nối phần cứng ảo, bảng định tuyến GPIO chống xung đột strapping, cấu hình `diagram.json`, `wokwi.toml` và các bước thực thi mô phỏng trên nền tảng Wokwi Simulator.

---

## 1. Danh Mục Thiết Bị Phần Cứng Ảo (Virtual Bill of Materials)

| Thiết Bị | Loại Linh Kiện Trong Wokwi | Số Lượng | Chức Năng |
| :--- | :--- | :---: | :--- |
| **Vi Điều Khiển** | `board-esp32-devkit-c-v4` | 1 | Bộ xử lý trung tâm 2 nhân 240MHz, FreeRTOS SMP |
| **Cảm Biến Siêu Âm** | `wokwi-hc-sr04` | 4 | Phát hiện xe tại 4 vị trí đỗ P01 .. P04 |
| **Đầu Đọc Thẻ RFID** | `board-mfrc522` | 2 | Quản lý phương tiện tại Cổng Vào (ENTRY) & Cổng Ra (EXIT) qua SPI |
| **Động Cơ Barrier** | `wokwi-servo` (SG90) | 2 | Đóng/mở thanh chắn cổng qua xung PWM LEDC 50Hz (0° – 90°) |
| **Cảm Biến An Toàn Cổng** | `wokwi-slide-switch` (Photoelectric Beam) | 2 | Mô phỏng chùm tia hồng ngoại chống kẹt xe dưới cánh chắn (Active LOW) |
| **Màn Hình Trạng Thái** | `wokwi-lcd1602` (I2C PCF8574) | 1 | Hiển thị số lượng chỗ trống và chỉ thị trạng thái cổng thời gian thực |

---

## 2. Bảng Phân Bổ Chân GPIO An Toàn (Strapping-Safe Pinout)

Thiết kế mạch tuân thủ nghiêm ngặt các quy tắc an toàn phần cứng của Espressif ESP32:
- **KHÔNG sử dụng GPIO 12:** (MTDI strapping pin). Nếu chân này bị kéo mức cao lúc boot, ESP32 sẽ chọn sai điện áp Flash 1.8V thay vì 3.3V, dẫn đến treo chip hoặc hỏng flash.
- **KHÔNG sử dụng GPIO 15:** (MTDO strapping pin). Tránh xung nhiễu PWM lúc khởi động làm giật cánh tay servo.
- **KHÔNG sử dụng GPIO 0, 2:** Tránh xung đột chế độ nạp firmware / bootloader.
- **Tận dụng tối đa 4 chân Input-Only (GPIO 34, 35, 36/VP, 39/VN):** 4 chân này không có mạch kéo (pull-up/down) và không thể xuất output, là lựa chọn hoàn hảo nhất cho 4 chân Echo của cảm biến siêu âm.

| Thiết Bị | Chân Linh Kiện | Chân GPIO ESP32 | Chiều Tín Hiệu | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :---: | :--- |
| **P01 HC-SR04** | TRIG / ECHO | **GPIO 25 / GPIO 34** | OUT / IN | Echo nối vào chân Input-Only an toàn |
| **P02 HC-SR04** | TRIG / ECHO | **GPIO 26 / GPIO 35** | OUT / IN | Echo nối vào chân Input-Only an toàn |
| **P03 HC-SR04** | TRIG / ECHO | **GPIO 27 / GPIO 36 (VP)** | OUT / IN | Echo nối vào chân Input-Only an toàn |
| **P04 HC-SR04** | TRIG / ECHO | **GPIO 32 / GPIO 39 (VN)** | OUT / IN | Echo nối vào chân Input-Only an toàn |
| **RFID SPI Bus** | SCK / MISO / MOSI | **GPIO 18 / 19 / 23** | VSPI Bus | Bus SPI dùng chung tốc độ 4MHz |
| **RFID Entry** | CS / RST | **GPIO 5 / GPIO 17** | OUT / OUT | Chip Select riêng biệt cho Cổng Vào |
| **RFID Exit** | CS / RST | **GPIO 4 / GPIO 17** | OUT / OUT | Chip Select riêng biệt cho Cổng Ra |
| **Servo Entry** | PWM (Signal) | **GPIO 13** | LEDC CH0 | PWM 50Hz (500µs: 0° Đóng; 1500µs: 90° Mở) |
| **Servo Exit** | PWM (Signal) | **GPIO 14** | LEDC CH1 | PWM 50Hz (Tránh GPIO 15 boot noise) |
| **Safety IR Entry** | Output (Signal) | **GPIO 33** | INPUT PULLUP | Active LOW (Mức 0 = Có vật cản) |
| **Safety IR Exit** | Output (Signal) | **GPIO 16** | INPUT PULLUP | Active LOW (Mức 0 = Có vật cản) |
| **LCD 1602 I2C** | SDA / SCL | **GPIO 21 / GPIO 22** | I2C Master | Tần số 100kHz, địa chỉ PCF8574 `0x27` |
| **Nguồn Cấp** | 5V / 3.3V / GND | **5V / 3V3 / GND** | Nguồn | Cấp đúng 3.3V cho RC522; 5V cho Servo, LCD, HC-SR04 |

---

## 3. Lộ Trình Triển Khai 2 Giai Đoạn (Two-Step Rollout)

### Bước 1: Mô Hình Kiểm Thử Tối Giểu (Minimal Baseline Setup)
Tập tin cấu hình: [`firmware/esp32/diagram-step1.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram-step1.json)
- Gồm: 1 ESP32, 1 HC-SR04 (P01), 1 MFRC522 (ENTRY), 1 Servo (ENTRY), 1 Công tắc cảm biến an toàn, 1 LCD I2C.
- Mục đích: Đo kiểm phản hồi Echo siêu âm, thử nghiệm quẹt thẻ RFID mẫu, kiểm chứng góc nâng/hạ servo và xác nhận khóa liên động an toàn trước khi mở rộng.

### Bước 2: Mô Hình Đầy Đủ Toàn Diện (Full Target Setup)
Tập tin cấu hình: [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json)
- Gồm: 1 ESP32, đủ 4 HC-SR04 (P01–P04), 2 MFRC522 (ENTRY & EXIT), 2 Servo Barrier, 2 Công tắc cảm biến an toàn, 1 LCD I2C.
- Mục đích: Mô phỏng toàn bộ luồng hoạt động của bãi đỗ xe 4 vị trí thời gian thực.

---

## 4. Hướng Dẫn Vận Hành Trên Wokwi Simulator

### Phương Án A: Chạy Trực Tiếp Bằng Wokwi Web (Khuyên Dùng Cho Mọi Máy)
1. Mở trình duyệt truy cập: [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32)
2. Nhấn vào tab **`diagram.json`** trong giao diện web Wokwi.
3. Sao chép toàn bộ nội dung từ file [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json) vào trình chỉnh sửa.
4. Bấm nút **Play (Run Simulation)** để bắt đầu mô phỏng tương tác.

### Phương Án B: Sử Dụng VS Code Với Extension Wokwi
1. Cài đặt extension: **Wokwi for VS Code** (ID: `wokwi.wokwi-vscode`).
2. Mở thư mục dự án trong VS Code.
3. Đảm bảo file [`wokwi.toml`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/wokwi.toml) và [`diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json) nằm tại thư mục `firmware/esp32/`.
4. Nhấn phím `F1`, gõ và chọn lệnh: `Wokwi: Start Simulator`.

### Phương Án C: Sử Dụng Wokwi CLI (`wokwi-cli`)
Nếu môi trường có cài đặt `wokwi-cli`:
```bash
cd firmware/esp32
wokwi-cli .
```

---

## 5. Hướng Dẫn Build Firmware Với ESP-IDF

### 5.1. Khi Máy Tính Đã Có ESP-IDF Cài Đặt
Mở ESP-IDF Command Prompt (hoặc terminal đã activate `export.bat` / `export.sh`):
```bash
cd firmware/esp32
idf.py set-target esp32
idf.py build
```
Kết quả build sẽ tạo ra tại thư mục `firmware/esp32/build/`:
- `smart_parking_esp32.elf`
- `flasher_args.json`
- `smart_parking_esp32.bin`
- `bootloader/bootloader.bin`
- `partition_table/partition-table.bin`

### 5.2. Build Bằng Docker Container (Dành Cho Máy Chưa Có Toolchain)
```bash
docker run --rm -v "D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32":/project -w /project espressif/idf:v5.3 idf.py build
```

---

## 6. Kết Nối Mạng Ảo Tới Backend (Wokwi Virtual Wi-Fi & Gateway)

Trong Wokwi Simulator:
1. Kết nối Wi-Fi sử dụng SSID mặc định: `"Wokwi-GUEST"` (không cần mật khẩu). ESP32 sẽ được cấp địa chỉ IP thông qua DHCP server ảo của Wokwi.
2. Để kết nối tới FastAPI Backend đang chạy trên máy chủ nội bộ (localhost port 8000), có 2 phương án:
   - **Phương án 1 (Wokwi IoT Gateway):** Cài đặt Wokwi IoT Gateway để bắc cầu mạng LAN ảo về máy host. Địa chỉ truy cập Backend từ Wokwi là `http://10.0.2.2:8000/api/v1`.
   - **Phương án 2 (Standalone Offline Mode):** Khi không có gateway, Firmware tự động kích hoạt cơ chế an toàn **Fail-safe Offline**. Hệ thống sẽ kiểm tra danh sách thẻ mẫu nội bộ (`30A-123.45`, `01:02:03:04`) để phục vụ việc demo cơ cấu nâng hạ barrier và hiển thị LCD mà không bị crash.
