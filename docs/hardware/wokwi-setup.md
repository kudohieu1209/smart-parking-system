# HƯỚNG DẪN MÔ PHỎNG PHẦN CỨNG WOKWI & SƠ ĐỒ ĐIỆN TỬ AN TOÀN CHO MẠCH THẬT
## SMART PARKING SYSTEM — ESP32 + FREERTOS + WOKWI HARDWARE SIMULATION

Tài liệu này cung cấp chi tiết:
1. Sơ đồ mô phỏng Wokwi 2 giai đoạn (`diagram-step1.json` và `diagram.json`).
2. **Sơ đồ an toàn điện áp cho mạch thật (Physical Hardware Safe Electrical Schematic)** nhằm bảo vệ vi điều khiển ESP32 khi triển khai từ mô phỏng sang phần cứng thực tế.
3. Bảng định tuyến GPIO strapping-safe, cơ chế bảo mật RFID offline và hướng dẫn tích hợp mạng Wokwi IoT Gateway.

---

## 1. Danh Mục Thiết Bị Phần Cứng (BOM — Bill of Materials)

| Thiết Bị | Linh Kiện Trong Wokwi | Linh Kiện Phần Cứng Thật | Điện Áp Hoạt Động | Giao Tiếp ESP32 | Ghi Chú An Toàn Điện |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Vi Điều Khiển** | `board-esp32-devkit-c-v4` | ESP32-WROOM-32D / DevKit V1/V4 | 3.3V (VCC logic) / 5V (VIN) | Core MCU | Chân GPIO chịu áp tối đa 3.6V |
| **Cảm Biến Ô Đỗ (x4)** | `wokwi-hc-sr04` (x4) | HC-SR04 / RCWL-1601 (x4) | 5.0V VCC | GPIO Trig (OUT), Echo (IN) | **BẮT BUỘC cầu phân áp Echo 5V -> 3.3V** |
| **Đầu Đọc Thẻ RFID (x2)** | `board-mfrc522` (x2) | RC522 RFID 13.56MHz Module (x2) | 3.3V VCC | VSPI (SCK, MOSI, MISO, CS, RST) | Cấp đúng nguồn 3.3V; không cấp 5V |
| **Động Cơ Barrier (x2)** | `wokwi-servo` (x2) | TowerPro SG90 / MG90S (x2) | 4.8V – 6.0V | GPIO 13, 14 (LEDC PWM 50Hz) | Dùng nguồn 5V ngoài riêng biệt + tụ lọc 1000µF |
| **Cảm Biến An Toàn (x2)** | `wokwi-slide-switch` (x2) | E18-D80NK / Photoelectric IR Beam | 5V / 3.3V | GPIO 33, 16 (INPUT PULLUP) | Active LOW (Mức 0 = Có vật cản kẹt xe) |
| **Màn Hình Trạng Thái** | `wokwi-lcd1602` (I2C) | LCD 1602 kèm Module I2C PCF8574T | 5.0V VCC | I2C (GPIO 21 SDA, GPIO 22 SCL) | Xử lý điện áp kéo trở I2C 5V tránh sốc GPIO |

---

## 2. Bảng Phân Bổ Chân GPIO Chống Xung Đột (Strapping-Safe Pinout)

Thiết kế mạch tuân thủ nghiêm ngặt các quy tắc an toàn phần cứng của Espressif ESP32:
- **KHÔNG sử dụng GPIO 12:** (MTDI strapping pin). Nếu chân này bị kéo mức cao lúc boot, ESP32 sẽ chọn sai điện áp Flash 1.8V thay vì 3.3V, dẫn đến treo chip hoặc hỏng flash.
- **KHÔNG sử dụng GPIO 15:** (MTDO strapping pin). Tránh xung nhiễu PWM lúc khởi động làm rung giật cánh tay servo.
- **KHÔNG sử dụng GPIO 0, 2:** Tránh xung đột chế độ nạp firmware / bootloader download mode.
- **Tận dụng 4 chân Input-Only (GPIO 34, 35, 36/VP, 39/VN):** 4 chân này không có mạch kéo nội và không thể xuất output, là lựa chọn chuẩn nhất cho 4 chân Echo của cảm biến siêu âm.
- **Lưu ý chân GPIO 5 (CS Cổng Vào):** GPIO 5 phát tín hiệu clock lúc boot. Cần gắn trở kéo lên 10kΩ nối lên 3.3V để giữ chân CS ở mức HIGH (Disable chip) khi khởi động.

| Thiết Bị | Chân Linh Kiện | Chân GPIO ESP32 | Chiều Tín Hiệu | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :---: | :--- |
| **P01 HC-SR04** | TRIG / ECHO | **GPIO 25 / GPIO 34** | OUT / IN | Echo qua cầu trở $1\text{k}\Omega / 2\text{k}\Omega$ vào chân Input-Only |
| **P02 HC-SR04** | TRIG / ECHO | **GPIO 26 / GPIO 35** | OUT / IN | Echo qua cầu trở $1\text{k}\Omega / 2\text{k}\Omega$ vào chân Input-Only |
| **P03 HC-SR04** | TRIG / ECHO | **GPIO 27 / GPIO 36 (VP)** | OUT / IN | Echo qua cầu trở $1\text{k}\Omega / 2\text{k}\Omega$ vào chân Input-Only |
| **P04 HC-SR04** | TRIG / ECHO | **GPIO 32 / GPIO 39 (VN)** | OUT / IN | Echo qua cầu trở $1\text{k}\Omega / 2\text{k}\Omega$ vào chân Input-Only |
| **RFID SPI Bus** | SCK / MISO / MOSI | **GPIO 18 / 19 / 23** | VSPI Bus | Bus SPI dùng chung, xung clock 4MHz |
| **RFID Entry** | CS / RST | **GPIO 5 / GPIO 17** | OUT / OUT | Chip Select riêng cổng vào (kèm trở kéo lên 10kΩ lên 3.3V) |
| **RFID Exit** | CS / RST | **GPIO 4 / GPIO 17** | OUT / OUT | Chip Select riêng biệt cho Cổng Ra |
| **Servo Entry** | PWM (Signal) | **GPIO 13** | LEDC CH0 | PWM 50Hz (500µs: 0° Đóng; 1500µs: 90° Mở) |
| **Servo Exit** | PWM (Signal) | **GPIO 14** | LEDC CH1 | PWM 50Hz (Tránh GPIO 15 boot noise) |
| **Safety IR Entry** | Output (Signal) | **GPIO 33** | INPUT PULLUP | Active LOW (Mức 0 = Có xe kẹt dưới barrier) |
| **Safety IR Exit** | Output (Signal) | **GPIO 16** | INPUT PULLUP | Active LOW (Mức 0 = Có xe kẹt dưới barrier) |
| **LCD 1602 I2C** | SDA / SCL | **GPIO 21 / GPIO 22** | I2C Master | Tần số 100kHz, địa chỉ PCF8574 `0x27` |
| **Nguồn Cấp** | 5V / 3.3V / GND | **5V / 3V3 / GND** | Nguồn | Cấp đúng 3.3V cho RC522; 5V ngoài cho Servo và HC-SR04 |

---

## 3. Sơ Đồ Điện Tử An Toàn Cho Mạch Thật (Physical Hardware Electrical Safe Schematic)

> [!CAUTION]
> **RỦI RO CHÁY HỎNG ESP32 TRÊN MẠCH THẬT:**
> Trong mô phỏng Wokwi, trình giả lập không tính toán giới hạn đánh thủng bán dẫn (overvoltage breakdown). Nhưng trên mạch thật:
> 1. HC-SR04 chạy nguồn 5V và chân ECHO phát mức áp 5V TTL.
> 2. Chân GPIO của ESP32 **KHÔNG CHỊU ĐƯỢC 5V** (giới hạn tuyệt đối là $3.6\text{V}$, điện áp danh định $3.3\text{V}$).
> 3. Cắm trực tiếp Echo 5V vào ESP32 sẽ phá hỏng cổng đệm đầu vào (input buffer) hoặc làm hỏng toàn bộ chip vi điều khiển!

### 3.1. Cầu Phân Áp Điện Trở Cho 4 Chân Echo (Voltage Divider)
Mỗi cảm biến HC-SR04 bắt buộc phải đi qua mạch cầu phân áp điện trở gồm $R_1 = 1\text{k}\Omega$ và $R_2 = 2\text{k}\Omega$:

```
HC-SR04 (5V)                   ESP32 (3.3V Logic)
+-------------+
|        ECHO |----[ R1: 1kΩ ]----+----> GPIO Echo (34, 35, 36, 39)
+-------------+                |
                               |
                            [ R2: 2kΩ ]
                               |
                              GND (Chung)
```

**Công thức tính điện áp ra:**
$$V_{\text{ESP32}} = V_{\text{ECHO}} \times \frac{R_2}{R_1 + R_2} = 5.0\text{V} \times \frac{2\text{k}\Omega}{1\text{k}\Omega + 2\text{k}\Omega} = 5.0\text{V} \times \frac{2}{3} \approx 3.33\text{V}$$
Điện áp $3.33\text{V}$ nằm hoàn toàn trong phạm vi an toàn chuẩn logic HIGH của ESP32 ($2.64\text{V} \le V_{IH} \le 3.6\text{V}$).

### 3.2. Xử Lý An Toàn Trở Kéo 5V Của Module I2C LCD PCF8574
- **Vấn đề:** Module PCF8574T thường được hàn sẵn 2 điện trở pull-up $4.7\text{k}\Omega$ (R8, R9) nối lên chân VCC 5V của module. Khi nối dây SDA/SCL về ESP32, điện áp 5V này sẽ tràn vào chân GPIO 21 và GPIO 22.
- **Giải pháp trên mạch thật (chọn 1 trong 3):**
  - **Cách 1 (Khuyên dùng):** Tháo (xả chì) 2 con trở dán $4.7\text{k}\Omega$ trên lưng module I2C và bật điện trở kéo nội `gpio_pullup_en()` lên 3.3V của ESP32.
  - **Cách 2:** Cấp nguồn VCC của module PCF8574 vào nguồn $3.3\text{V}$ của ESP32 (lưu ý chỉnh biến trở xanh ở lưng để đảm bảo độ tương phản màn hình hiển thị rõ chữ).
  - **Cách 3:** Dùng module chuyển đổi mức logic 2 chiều I2C (Bi-directional Logic Level Shifter) 4 kênh (BSS138).

### 3.3. Cô Lập Nguồn Nuôi Động Cơ Servo (Chống Reset Brownout)
- Động cơ RC Servo SG90 có dòng đỉnh khởi động lên đến $800\text{mA} - 1000\text{mA}$ cho mỗi con. Khi cả hai barrier cùng nâng, dòng tiêu thụ tức thời có thể đạt $2\text{A}$.
- Nếu cấp nguồn servo từ chân 5V của ESP32 (lấy qua cổng microUSB máy tính), điện áp sẽ bị sụt mạnh khiến ESP32 bị reset liên tục (`Brownout detector was triggered`).
- **Sơ đồ cấp nguồn đúng:**
  - Nguồn 5V 2A ngoài (Adapter/Buck Regulator) cấp riêng cho chân VCC đỏ của 2 Servo SG90.
  - Đấu nối toàn bộ GND của nguồn 5V ngoài với GND của ESP32 (Common Ground).
  - Đặt thêm 1 tụ điện hóa dung lượng $1000\mu\text{F} / 16\text{V}$ mắc song song giữa đường 5V và GND của Servo để đệm dòng tải tức thời.

---

## 4. Lộ Trình Triển Khai 2 Giai Đoạn (Two-Step Rollout)

### Bước 1: Mô Hình Tối Giản Đo Kiểm Cơ Bản (`diagram-step1.json`)
Tập tin cấu hình: [`firmware/esp32/diagram-step1.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram-step1.json)
- **Thành phần:** 1 ESP32, 1 Cảm biến siêu âm P01, 1 Đầu đọc RFID Cổng Vào (UID: `30:A1:23:45`), 1 Servo Cổng Vào, 1 Công tắc an toàn quang, 1 LCD 1602 I2C.
- **Mục tiêu:** Đo kiểm chính xác phản hồi Echo, kiểm tra quét thẻ RFID mẫu, kiểm chứng góc nâng/hạ LEDC PWM 50Hz và xác nhận khóa an toàn non-blocking 3s.

### Bước 2: Mô Hình Đầy Đủ Toàn Diện (`diagram.json`)
Tập tin cấu hình: [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json)
- **Thành phần:** 1 ESP32, 4 Cảm biến siêu âm P01–P04, 2 Đầu đọc RFID (Cổng vào: `30:A1:23:45`, Cổng ra: `01:02:03:04`), 2 Động cơ Servo Barrier, 2 Công tắc cảm biến an toàn, 1 LCD 1602 I2C.
- **Mục tiêu:** Mô phỏng hoàn chỉnh luồng nghiệp vụ đỗ xe 4 vị trí thời gian thực.

---

## 5. Chuẩn Hóa Mã Thẻ RFID & Cơ Chế Bảo Mật Fail-Safe

### 5.1. Bảng Chuẩn Hóa Mã Thẻ (Standardized Hex UIDs)
Hệ thống chuẩn hóa đồng bộ mã thẻ RFID 4 byte Hex trên cả 3 tầng: ESP32 Firmware, Wokwi Simulator và FastAPI Backend:

| Thẻ RFID | Mã Hex Chuẩn | Biển Số Xe Đăng Ký | Chủ Phương Tiện | Hạng Thẻ |
| :--- | :---: | :---: | :--- | :---: |
| **Thẻ Cổng Vào (Wokwi Entry)** | `30:A1:23:45` | **30A-123.45** | Doan Minh Duc | VIP |
| **Thẻ Cổng Ra (Wokwi Exit)** | `01:02:03:04` | **29C-678.90** | Vu Hoang Long | STANDARD |
| **Thẻ Mẫu Phần Mềm 01** | `RFID-DEMO-01` | **30A-123.45** | Nguyen Van An | VIP |
| **Thẻ Mẫu Phần Mềm 02** | `RFID-DEMO-02` | **29C-678.90** | Tran Thi Binh | VIP |

### 5.2. Chính Sách Bảo Mật Offline (Hardware Fail-Safe Security)
- **Trong Chế Độ Phần Cứng Thật (Hardware Mode):**
  Khi Wi-Fi mất kết nối hoặc Backend FastAPI offline, Firmware ESP32 **BẮT BUỘC TỪ CHỐI TẤT CẢ** các lượt quẹt thẻ (`*out_allowed = false`, trả về `ESP_ERR_INVALID_STATE`). Thanh chắn barrier tuyệt đối không mở tự do.
- **Trong Chế Độ Mô Phỏng Độc Lập (Simulation Offline Demo):**
  Chỉ khi người lập trình bật tường minh cờ biên dịch `CONFIG_SMART_PARKING_SIMULATION_OFFLINE_DEMO` trong `idf.py menuconfig`, firmware mới cho phép mở barrier offline với danh sách thẻ trắng chính xác (`30:A1:23:45` hoặc `01:02:03:04`). Không chấp nhận bất kỳ chuỗi UID ngẫu nhiên nào khác chứa "DEMO" hay "30A".

---

## 6. Hướng Dẫn Vận Hành Trên Wokwi Simulator

### Phương Án A: Chạy Trực Tiếp Bằng Wokwi Web (Khuyên Dùng Cho Mọi Máy)
1. Mở trình duyệt truy cập: [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32)
2. Nhấn vào tab **`diagram.json`** trong giao diện web Wokwi.
3. Sao chép toàn bộ nội dung từ file [`firmware/esp32/diagram-step1.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram-step1.json) (bước 1) hoặc [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json) (bước 2) vào trình soạn thảo Wokwi.
4. Bấm nút **Play (Run Simulation)** để bắt đầu mô phỏng tương tác.

### Phương Án B: Sử Dụng VS Code Với Extension Wokwi
1. Cài đặt extension: **Wokwi for VS Code** (ID: `wokwi.wokwi-vscode`).
2. Mở thư mục dự án trong VS Code.
3. Đảm bảo file [`wokwi.toml`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/wokwi.toml) và [`diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json) nằm tại thư mục `firmware/esp32/`.
4. Nhấn phím `F1`, gõ và chọn lệnh: `Wokwi: Start Simulator`.

### Phương Án C: Kết Nối Mạng Ảo Wokwi IoT Gateway Về Localhost Backend
1. Để ESP32 ảo kết nối được vào FastAPI Backend trên máy tính host (`http://127.0.2.1:8000`), tải và khởi chạy [Wokwi IoT Gateway](https://wokwi.com/tools/iot-gateway).
2. ESP32 kết nối vào Wi-Fi ảo SSID: `Wokwi-GUEST` (không pass).
3. Địa chỉ gọi Backend từ ESP32 Wokwi là: `http://10.0.2.2:8000/api/v1` (IP gateway ảo `10.0.2.2` tự động trỏ về `localhost` máy tính).
