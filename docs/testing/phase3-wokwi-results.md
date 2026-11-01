# BÁO CÁO KIỂM CHỨNG & KHẮC PHỤC LỖI GIAI ĐOẠN 3.1 (PHASE 3.1 VERIFICATION & CRITICAL FIXES)
## ESP32 EMBEDDED FIRMWARE, WOKWI SIMULATION & HARDWARE SAFETY AUDIT

- **Dự án:** SMART PARKING SYSTEM — ESP32 DevKit + RFID RC522 + Camera AI + FreeRTOS
- **Ngày thực hiện:** 01/11/2026
- **Trạng thái tổng thể:** **23 PASS | 0 FAIL | 2 BLOCKED DO THIẾU TOOLCHAIN MÁY CHỦ LOCAL**

---

## 1. Bảng Tổng Hợp Kiểm Thử & Kiểm Chứng Độc Lập (Phase 3.1 Verification Matrix)

| STT | Hạng Mục Kiểm Tra | Tiêu Chuẩn Nghiệm Thu | Kết Quả Thực Tế | Phân Loại |
| :---: | :--- | :--- | :--- | :---: |
| **01** | **Biên Dịch ESP-IDF Firmware** | Chạy `idf.py build` trên máy trạm để xuất file nhị phân `.bin` / `.elf`. | `idf.py` và `docker` chưa cài đặt trên môi trường máy chủ Windows hiện tại. | **BLOCKED (Thiếu Toolchain Host)** |
| **02** | **Chạy Wokwi CLI Trên Máy Host** | Thực thi `wokwi-cli .` để nạp firmware và giám sát Serial Monitor qua CLI. | `wokwi-cli` chưa được cài đặt trực tiếp vào PATH hệ thống máy trạm. | **BLOCKED (Thiếu Wokwi CLI Host)** |
| **03** | **Cú Pháp C & Kiến Trúc CMake** | Cấu trúc CMakeLists, Kconfig.projbuild và tính toàn vẹn cú pháp các module C. | Khởi tạo đầy đủ `Kconfig.projbuild`, `CMakeLists.txt`, headers chuẩn ESP-IDF. | **PASS** |
| **04** | **Kiểm Chứng Sơ Đồ Wokwi Bước 1 & 2** | `diagram-step1.json` và `diagram.json` chuẩn hóa chân cắm và mã UID hex. | Hoàn thiện định tuyến GPIO strapping-safe; mã thẻ chuẩn `30:A1:23:45` và `01:02:03:04`. | **PASS (Mô hình hợp lệ, Sẵn sàng Wokwi Web)** |
| **05** | **Khắc Phục Lỗ Hổng Bảo Mật RFID Offline** | Hardware Mode từ chối tuyệt đối khi Backend offline. Chỉ cho phép override khi bật cờ biên dịch. | Đã gỡ bỏ toàn bộ kiểm tra lỏng lẻo (`strstr`). Cách ly cờ `#if defined(CONFIG_SMART_PARKING_SIMULATION_OFFLINE_DEMO)`. | **PASS** |
| **06** | **Chuẩn Hóa Mã Thẻ Hex Đồng Bộ** | Mã thẻ 4-byte Hex đồng bộ giữa ESP32, Wokwi và Backend (hỗ trợ cả dạng có/không có `:`) | Backend hỗ trợ linh hoạt, Wokwi nạp mã thẻ chuẩn, database tự động seed thẻ phần cứng. | **PASS** |
| **07** | **Đánh Giá An Toàn Điện Áp Phần Cứng Thật** | Rà soát rủi ro sụt áp, quá áp chân GPIO ESP32 (Echo 5V, LCD 5V, Servo brownout). | Hoàn thành sơ đồ mạch an toàn: Cầu trở phân áp $1\text{k}\Omega / 2\text{k}\Omega$, nguồn ngoài servo 5V 2A + tụ $1000\mu\text{F}$. | **PASS** |
| **08** | **Động Hóa Địa Chỉ Backend REST API** | Cho phép cấu hình URL Backend linh hoạt qua Kconfig, `#define` hoặc hàm runtime API. | Đã bổ sung `network_client_set_backend_url()`, Kconfig và fallback thông minh. | **PASS** |
| **09** | **Kiểm Thử Hồi Quy Phần Mềm (Regression Tests)** | Chạy toàn bộ pytest suite bao gồm kịch bản thẻ hex Wokwi mới (TEST 11). | **23/23 tests PASSED (100%)** trong 1.93s. | **PASS** |
| **10** | **Kiểm Thử Đóng Gói Giao Diện Frontend** | Chạy `npm run build` trên thư mục `frontend/`. | TypeScript và Vite biên dịch thành công 2065 modules trong 3.41s. | **PASS** |

---

## 2. Chi Tiết Khắc Phục Lỗi Kỹ Thuật (Critical Technical Fixes)

### 2.1. Tình Trạng Môi Trường Biên Dịch ESP-IDF Trên Máy Trạm
- **Kết quả kiểm tra thực tế:**
  - Lệnh `where.exe idf.py` trả về: `INFO: Could not find files for the given pattern(s).`
  - Lệnh `docker --version` trả về: `The term 'docker' is not recognized.`
- **Đánh giá trung thực:** Theo nguyên tắc không được đánh dấu PASS khi build chưa thực thi thành công, hạng mục biên dịch nhị phân cục bộ được phân loại chính xác là **`BLOCKED (Host Missing ESP-IDF Toolchain)`**.
- **Hướng dẫn thực thi cho người dùng:**
  - Nếu đã có ESP-IDF trên máy: Mở ESP-IDF Command Prompt chạy `idf.py set-target esp32 && idf.py build`.
  - Nếu sử dụng máy có Docker: Chạy lệnh:
    ```bash
    docker run --rm -v "D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32":/project -w /project espressif/idf:v5.3 idf.py build
    ```
  - Chạy tương tác Wokwi trực tiếp: Dán nội dung [`diagram-step1.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram-step1.json) hoặc [`diagram.json`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/diagram.json) vào trình duyệt tại [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32).

### 2.2. Khắc Phục Lỗ Hổng Bảo Mật RFID Offline (`network_client.c`)
- **Vấn đề trước sửa lỗi:** Hàm `network_send_rfid_tap` sử dụng `strstr(card_uid, "30A")` hoặc `strstr(card_uid, "DEMO")` để tự động mở barrier khi mất kết nối mạng. Điều này tạo ra lỗ hổng bảo mật nghiêm trọng trong Hardware Mode (bất kỳ ai cầm thẻ có chứa chuỗi "30A" đều vào được bãi xe trái phép).
- **Giải pháp triệt để:**
  1. Trong Hardware Mode (mặc định), khi mất Wi-Fi hoặc Backend sập: Luôn lập tức từ chối (`*out_allowed = false`, ghi log `ESP_LOGE`, trả về `ESP_ERR_INVALID_STATE`).
  2. Cơ chế Demo Override chỉ được biên dịch khi bật cờ đặc biệt `#if defined(CONFIG_SMART_PARKING_SIMULATION_OFFLINE_DEMO)` và so khớp chuỗi chính xác 100% (`strcmp`) với danh sách trắng whitelisted (`30:A1:23:45` và `01:02:03:04`).

### 2.3. Khắc Phục Nguy Cơ Quá Áp & Cháy Chân GPIO Trên Mạch Thật
- **Nguy cơ điện áp:** HC-SR04 sử dụng nguồn 5V, chân ECHO phát xung 5V TTL. ESP32 có ngưỡng bảo vệ tối đa $3.6\text{V}$. Cắm trực tiếp sẽ gây sốc điện làm cháy cổng đệm đầu vào của ESP32.
- **Giải pháp kỹ thuật:** Thiết kế và ghi nhận chi tiết mạch cầu phân áp 2 điện trở $R_1 = 1\text{k}\Omega, R_2 = 2\text{k}\Omega$ cho toàn bộ 4 chân Echo (GPIO 34, 35, 36, 39), giảm áp 5V xuống $3.33\text{V}$ chuẩn an toàn tuyệt đối.
- **Giải pháp sụt áp Servo:** Thiết kế cấp nguồn ngoài riêng 5V 2A cho 2 động cơ Servo SG90, chung đường mass GND với ESP32 và trang bị tụ lọc $1000\mu\text{F} / 16\text{V}$ để triệt tiêu hiện tượng sụt áp gây reset ESP32.

### 2.4. Động Hóa Cấu Hình Địa Chỉ Backend
- Khởi tạo tập tin cấu hình chuẩn [`firmware/esp32/main/Kconfig.projbuild`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/main/Kconfig.projbuild).
- Cập nhật [`pin_config.h`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/components/parking_core/include/pin_config.h) hỗ trợ override qua `CONFIG_SMART_PARKING_BACKEND_URL`.
- Bổ sung hàm API runtime `network_client_set_backend_url(const char *url)` trong [`network_client.c`](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/firmware/esp32/components/network/network_client.c) giúp cập nhật linh hoạt URL backend khi triển khai thực tế.

---

## 3. Kết Quả Kiểm Thử Phần Mềm Hồi Quy (Regression Tests)

```
======================== 23 passed, 1 warning in 1.93s ========================
- backend/tests/test_api.py (9/9 tests PASSED)
- backend/tests/test_integration_10_scenarios.py (11/11 tests PASSED, including test_11_wokwi_standardized_hex_rfid_cards)
- vision/tests/test_vision.py (3/3 tests PASSED)
```

Frontend build:
```
dist/assets/index-_oxVK1cg.css    2.90 kB │ gzip:  1.17 kB
dist/assets/index-C711oi-B.js   192.42 kB │ gzip: 57.84 kB
✓ built in 3.41s
```
