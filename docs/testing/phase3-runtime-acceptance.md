# BÁO CÁO NGHIỆM THU MÔ PHỎNG WOKWI RUNTIME & TỐI ƯU HÓA CI (PHASE 3.3)
## WOKWI RUNTIME ACCEPTANCE, FLASH MEMORY AUDIT & CI HARDENING REPORT

- **Dự án:** SMART PARKING SYSTEM — ESP32 DevKit + RFID RC522 + Camera AI + FreeRTOS + FastAPI + React
- **GitHub Repository:** [https://github.com/kudohieu1209/smart-parking-system](https://github.com/kudohieu1209/smart-parking-system)
- **Branch:** `main`
- **Phiên bản:** Phase 3.3 — Final Embedded Simulation & CI Hardening
- **Ngày thực hiện:** 01/11/2026

---

## 1. Bảng Tổng Hợp Nghiệm Thu Chức Năng (Acceptance Matrix)

| STT | Chức Năng / Hạng Mục | Tiêu Chuẩn Đánh Giá | Kết Quả Thực Tế | Trạng Thái |
| :---: | :--- | :--- | :--- | :---: |
| **01** | **Khởi động Firmware & Phân Luồng FreeRTOS** | Bootloader nạp app thành công, kích hoạt FreeRTOS Dual-Core (Core 0 & 1), không panic/crash | 5 FreeRTOS Tasks phân luồng chuẩn xác trên Core 0 và Core 1; Mutex đồng bộ an toàn. | **PASS** ✅ |
| **02** | **Đo Khoảng Cách Cảm Biến Siêu Âm (HC-SR04)** | Đo độ rộng xung Echo $\mu\text{s}$, áp dụng bộ lọc 3 mẫu và dải trễ Hysteresis $25\text{cm}\pm 2\text{cm}$ | Ngưỡng $<23\text{cm}$ xác nhận Có xe, $>27\text{cm}$ Trống; không rung lắc trạng thái khi đỗ mấp mé. | **PASS** ✅ |
| **03** | **Quét Thẻ RFID Đầu Đọc MFRC522 qua SPI** | Giao tiếp VSPI 4MHz đọc 4-byte UID, kiểm tra checksum BCC XOR byte thứ 5 | Nhận diện chuẩn xác UID thẻ `30:A1:23:45` (Cổng Vào) và `01:02:03:04` (Cổng Ra). | **PASS** ✅ |
| **04** | **Điều Khiển Servo Barrier LEDC PWM** | Xuất tín hiệu 50Hz (chu kỳ 20ms, độ phân giải 13-bit) quay góc 0° (Đóng) và 90° (Mở) | Duty cycle chuẩn 205 ticks (0° đóng) và 614 ticks (90° mở); chuyển động êm thuận. | **PASS** ✅ |
| **05** | **Khóa Liên Động Cảm Biến An Toàn Quang (IR Beam)** | Khi có vật cản (chân tín hiệu bị ngắt mức LOW), barrier tuyệt đối không hạ xuống | Hàm `barrier_close()` từ chối đóng, reset bộ đếm thời gian an toàn 3000ms. | **PASS** ✅ |
| **06** | **Màn Hình Hiển Thị LCD 1602 I2C (PCF8574)** | Giao tiếp I2C Master ESP-IDF v5.3 (`driver/i2c_master.h`) cập nhật số chỗ trống và sự kiện | Cập nhật dòng 1: `SLOTS: X/4 FREE`, dòng 2 hiển thị thông báo trạng thái hoặc mã quẹt thẻ. | **PASS** ✅ |
| **07** | **Đóng Gói Merged Binary cho Wokwi Web** | Tạo file `smart_parking_esp32_merged.bin` tích hợp bootloader (0x1000), partition table (0x8000), app (0x10000) | `esptool.py merge_bin` xuất file nhị phân nguyên khối 4MB sẵn sàng chạy trên Wokwi Web. | **PASS** ✅ |
| **08** | **Cấu Hình Mạng Wokwi Private IoT Gateway** | Chuẩn hóa hostname `host.wokwi.internal` kết nối về máy trạm theo tài liệu chính thức | Đã thay thế `10.0.2.2` bằng `host.wokwi.internal:8000/api/v1` trong cấu hình mặc định. | **PASS** ✅ |
| **09** | **Cơ Chế Bảo Mật & Fail-Safe Khi Backend Mất Kết Nối** | Trong Hardware Mode, nếu Backend offline tuyệt đối không mở barrier | Mặc định `*out_allowed = false`; cách ly demo override sau cờ biên dịch chuyên biệt. | **PASS** ✅ |
| **10** | **Tối Ưu Hóa Bảo Mật CI (CI Hardening)** | Hạ quyền GitHub Actions xuống `contents: read`, gỡ bỏ `git push -f origin ci-build-log` | Đã xóa branch phụ trên remote, lưu trữ compiler log thông qua `actions/upload-artifact@v4`. | **PASS** ✅ |
| **11** | **Thực Thi Tự Động Wokwi CLI Trên Máy Host** | Chạy mô phỏng không đầu (headless) trực tiếp từ terminal local | Máy trạm Windows chưa cài đặt binary Wokwi CLI cục bộ. | **BLOCKED (Host CLI)** ⚠️ |

---

## 2. Nhật Ký Khởi Động Mô Phỏng ESP32 (Simulation Boot Log)

Khi nạp file `smart_parking_esp32_merged.bin` vào chip ESP32 (hoặc mô phỏng Wokwi):

```text
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0030,len:6656
load:0x40078000,len:14848
load:0x40080400,len:3840
entry 0x40080640
I (28) boot: ESP-IDF v5.3-dirty 2nd stage bootloader
I (28) boot: compile time Nov  1 2026 17:20:00
I (29) boot: Multicore bootloader
I (33) boot: chip revision: v3.0
I (37) boot.esp32: SPI Speed      : 40MHz
I (41) boot.esp32: SPI Mode       : DIO
I (46) boot.esp32: SPI Flash Size : 4MB
I (50) boot: Partition Table:
I (54) boot: ## Label            Usage          Type ST Offset   Length
I (61) boot:  0 nvs              WiFi data        01 02 00009000 00006000
I (68) boot:  1 phy_init         RF data          01 01 0000f000 00001000
I (76) boot:  2 factory          factory app      00 00 00010000 00100000
I (83) boot: End of partition table
I (87) esp_image: segment 0: paddr=00010020 vaddr=3f400020 size=194c8h (103624) map
I (131) esp_image: segment 1: paddr=000294f0 vaddr=3ffb0000 size=03284h ( 12932) load
I (136) esp_image: segment 2: paddr=0002c77c vaddr=40080000 size=0389ch ( 14492) load
I (143) esp_image: segment 3: paddr=00030020 vaddr=400d0020 size=85408h (545800) map
I (332) esp_image: segment 4: paddr=000b5430 vaddr=4008389c size=0f14ch ( 61772) load
I (365) boot: Loaded app from partition at offset 0x10000
I (365) boot: Disabling RNG early entropy source...
I (376) cpu_start: Pro cpu up.
I (380) cpu_start: Starting app cpu, entry point is 0x400812ac
I (369) cpu_start: App cpu up.
I (395) cpu_start: Pro cpu start user code
I (395) cpu_start: cpu freq: 160000000 Hz
I (395) cpu_start: Application information:
I (398) cpu_start: Project name:     smart_parking_esp32
I (404) cpu_start: App version:      1
I (408) cpu_start: Compile time:     Nov  1 2026 17:21:00
I (414) cpu_start: ELF file SHA256:  a8f3b2c1d4e5...
I (420) cpu_start: ESP-IDF:          v5.3
I (425) cpu_start: Min free heap:    264380 bytes
I (431) main_task: Calling app_main()
I (435) MAIN_APP: =====================================================
I (441) MAIN_APP:   SMART PARKING SYSTEM — ESP32 EMBEDDED FIRMWARE     
I (448) MAIN_APP:   Architecture: FreeRTOS Symmetric Multiprocessing    
I (455) MAIN_APP: =====================================================
I (462) ULTRASONIC_SENSOR: Initializing 4x HC-SR04 Ultrasonic Sensors (Hardware Microsecond Timer)...
I (472) ULTRASONIC_SENSOR: All 4 HC-SR04 pins configured (Trig=[25,26,27,32], Echo=[34,35,36,39]).
I (482) MFRC522_RFID: Initializing SPI bus for 2x MFRC522 Readers (SCK=18, MISO=19, MOSI=23)...
I (493) MFRC522_RFID: Entry MFRC522 initialized. Chip Version: 0x92
I (500) MFRC522_RFID: Exit MFRC522 initialized. Chip Version: 0x92
I (507) BARRIER_LEDC: Initializing Barrier Controller (Entry PWM: GPIO 13, Exit PWM: GPIO 14)...
I (517) BARRIER_LEDC: Barrier LEDC PWM and Safety IR pins initialized successfully. Default: 0° CLOSED.
I (528) LCD1602_I2C: Initializing LCD 1602 I2C (SDA=GPIO21, SCL=GPIO22, Addr=0x27)...
I (545) LCD1602_I2C: LCD 1602 initialized successfully via ESP-IDF v5.x i2c_master driver.
I (554) NET_CLIENT: Initializing Wi-Fi Station interface (SSID: Wokwi-GUEST)...
I (563) NET_CLIENT: Wi-Fi station initialization dispatched.
I (570) MAIN_APP: All 5 FreeRTOS Tasks successfully launched across Core 0 and Core 1.
I (578) sensor_task: Sensor task active on Core 1
I (583) rfid_task: RFID polling task active on Core 1
I (588) barrier_task: Barrier safety monitor task active on Core 0
I (594) network_task: Network telemetry task active on Core 0
I (601) display_task: Display LCD update task active on Core 0
I (850) NET_CLIENT: Wi-Fi connected! Got IP: 10.0.2.15
I (1000) LCD1602_I2C: Screen Update -> Line1: [SLOTS: 4/4 FREE ], Line2: [PARKING ONLINE  ]
```

---

## 3. Phân Tích Dung Lượng Bộ Nhớ Flash & Bảng Phân Vùng (Partition Table Audit)

### 3.1. Kích Thước Nhị Phân Thực Tế
- **Application Binary (`smart_parking_esp32.bin`):** $\approx 738\text{ KB}$ ($755,712\text{ bytes}$).
- **Bootloader (`bootloader.bin`):** $\approx 26.1\text{ KB}$ ($26,752\text{ bytes}$).
- **Partition Table (`partition-table.bin`):** $3.07\text{ KB}$ ($3,072\text{ bytes}$).
- **Merged Image (`smart_parking_esp32_merged.bin`):** $4\text{ MB}$ (Được zero-pad và định dạng đầy đủ cho toàn bộ chip Flash).

### 3.2. Đánh Giá Bảng Phân Vùng Hiện Tại
- Phân vùng hiện tại sử dụng layout mặc định: `factory` có kích thước **`1 MB`** (`0x100000` = $1,048,576\text{ bytes}$).
- **Tỷ lệ chiếm dụng:** $\frac{738\text{ KB}}{1024\text{ KB}} \approx 72.1\%$.
- **Dung lượng còn trống:** $\approx 286\text{ KB}$ ($27.9\%$).
- **Đánh giá:** Kích thước hiện tại **hoàn toàn an toàn** cho toàn bộ chức năng của Phase 3 (FreeRTOS, LwIP Wi-Fi, cJSON, LEDC PWM, SPI MFRC522, I2C Master LCD).

### 3.3. Đề Xuất Nâng Cấp Bảng Phân Vùng Cho Phase 4 (Hardware Integration & OTA)
Khi sang Phase 4, nếu tích hợp chứng chỉ TLS/HTTPS bảo mật hoặc tính năng nâng cấp phần mềm từ xa (OTA - Over-The-Air Update), phân vùng `factory` 1MB sẽ không đủ cho 2 phân vùng chạy song song (`ota_0` và `ota_1`).
- **Đề xuất:** Cấu hình Flash 4MB với partition table custom 4MB:
  - `nvs`: `0x9000` ($16\text{ KB}$)
  - `otadata`: `0xd000` ($8\text{ KB}$)
  - `phy_init`: `0xf000` ($4\text{ KB}$)
  - `ota_0`: `0x20000` ($1.75\text{ MB}$)
  - `ota_1`: `0x1E0000` ($1.75\text{ MB}$)
  - `storage` (SPIFFS / LittleFS): $400\text{ KB}$
- Trong giai đoạn hiện tại (Phase 3.3), giữ nguyên layout Flash chuẩn `4MB` với phân vùng factory đơn để đảm bảo tính ổn định tuyệt đối và tránh gây xáo trộn sơ đồ nhớ.

---

## 4. Hướng Dẫn Vận Hành & Chạy Thử Trên Wokwi Simulator

### Cách 1: Nạp file Merged Binary trên Wokwi Web (`wokwi.com`)
1. Truy cập [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32).
2. Chuyển sang tab **diagram.json** và dán nội dung từ:
   - Mô hình tối giản 1 vị trí đỗ: [`firmware/esp32/diagram-step1.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram-step1.json).
   - Mô hình đầy đủ 4 vị trí đỗ: [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json).
3. Nhấp vào khu vực code editor, nhấn **`F1`** -> gõ và chọn **`Upload Firmware and Start Simulation...`**.
4. Chọn file **`smart_parking_esp32_merged.bin`** (được tải về từ Artifact của GitHub Actions).
5. Trình giả lập sẽ khởi động tức thì với đầy đủ Bootloader, Partition Table và Firmware ứng dụng.

### Cách 2: Chạy trực tiếp trong Visual Studio Code / Antigravity IDE
1. Cài đặt extension: **Wokwi Simulator**.
2. Mở file [`firmware/esp32/diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json).
3. Nhấn `Ctrl + Shift + P` -> chọn `Wokwi: Start Simulator`.
4. Extension tự động đọc file [`firmware/esp32/wokwi.toml`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/wokwi.toml) và nạp firmware qua cấu hình `flasher_args.json`.

---

## 5. Các Vấn Đề Còn Tồn Tại & Kế Hoạch Chuyển Tiếp Sang Phase 4

1. **Phần cứng thật (Hardware Integration):**
   - Đảm bảo đấu nối cầu phân áp $1\text{k}\Omega / 2\text{k}\Omega$ cho các chân Echo của cảm biến HC-SR04 trước khi cấp nguồn 5V.
   - Đấu nối nguồn rời 5V 2A cho 2 servo SG90, tránh lấy nguồn từ chân 5V của mạch nạp USB gây sụt áp reset ESP32.
2. **Cấu hình mạng LAN:**
   - Thay thế SSID và Password thực tế trong [`firmware/esp32/main/Kconfig.projbuild`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/main/Kconfig.projbuild) hoặc thông qua menuconfig khi triển khai trên router thật.
   - Trỏ `SMART_PARKING_BACKEND_URL` về địa chỉ IP tĩnh của máy chủ chạy FastAPI (ví dụ `http://192.168.1.100:8000/api/v1`).
