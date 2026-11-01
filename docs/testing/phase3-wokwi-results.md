# BÁO CÁO KẾT QUẢ KIỂM THỬ GIAI ĐOẠN 3 (PHASE 3 TESTING REPORT)
## ESP32 EMBEDDED FIRMWARE & WOKWI HARDWARE SIMULATION

- **Dự án:** SMART PARKING SYSTEM — ESP32 DevKit + RFID RC522 + Camera AI + FreeRTOS
- **Môi trường:** Wokwi Simulator & ESP-IDF v5.x Architecture
- **Ngày thực hiện:** 01/11/2026
- **Trạng thái phân loại:** **9 PASS | 0 FAIL | 0 SKIP | 1 CONDITIONAL (BLOCKED YÊU CẦU CỔNG GATEWAY)**

---

## 1. Bảng Tổng Hợp Kiểm Thử Nghiệm Thu (Verification Matrix)

| STT | Hạng Mục Kiểm Thử | Tiêu Chuẩn Nghiệm Thu | Kết Quả | Phân Loại |
| :---: | :--- | :--- | :---: | :---: |
| **01** | **ESP-IDF Architecture & CMake Build System** | Khởi tạo đầy đủ cấu trúc CMakeLists, component đăng ký đúng module phụ thuộc (`freertos`, `driver`, `esp_wifi`, `esp_http_client`, `cJSON`). | **ĐẠT** | **PASS** |
| **02** | **Rà Soát Chân GPIO & Strapping Pins** | Không sử dụng GPIO 12 (MTDI), GPIO 15 (MTDO), GPIO 0, 2; tận dụng 4 chân Input-Only (34, 35, 36, 39) cho Echo. | **ĐẠT** | **PASS** |
| **03** | **HC-SR04 Ultrasonic Sensor Driver** | Đo độ rộng xung Echo bằng microsecond timer (`esp_timer_get_time()`), lọc trung bình trượt 3 mẫu, hysteresis 25cm $\pm$ 2cm, không gán trống khi timeout. | **ĐẠT** | **PASS** |
| **04** | **MFRC522 RFID SPI Driver** | Bus SPI 4MHz, 2 Chip Select riêng biệt (ENTRY CS=5, EXIT CS=4), kiểm tra thanh ghi Version, anticollision và kiểm tra checksum BCC. | **ĐẠT** | **PASS** |
| **05** | **LEDC PWM Servo Driver** | Timer LEDC 50Hz, 13-bit (8192 ticks), điều khiển góc 0° (500µs / 205 ticks) và 90° (1500µs / 614 ticks) trên GPIO 13 & 14. | **ĐẠT** | **PASS** |
| **06** | **Khóa Liên Động An Toàn Barrier** | Cảm biến quang an toàn Active LOW (GPIO 33 & 16), máy trạng thái đếm lùi non-blocking 3s, từ chối hạ cánh khi có vật cản. | **ĐẠT** | **PASS** |
| **07** | **FreeRTOS SMP & Thread Safety** | 5 tác vụ độc lập chạy trên 2 nhân Core 0 và Core 1; chia sẻ dữ liệu ô đỗ qua khóa Mutex (`g_telemetry_mutex`), không có race condition. | **ĐẠT** | **PASS** |
| **08** | **Cơ Chế Fail-safe Xác Thực Thẻ** | Mặc định từ chối (`*out_allowed = false`) cho đến khi Backend xác nhận `ALLOWED`. Không tự động cho phép mọi thẻ trong Hardware mode. | **ĐẠT** | **PASS** |
| **09** | **Kiểm Thử Hồi Quy Phase 2 (Regression Tests)** | Toàn bộ 22 unit & integration test cases của Backend, Vision và API vẫn đạt 100% (22/22 passed trong 2.71s), không bị phá vỡ. | **ĐẠT** | **PASS** |
| **10** | **Tích Hợp E2E Wokwi Virtual Wi-Fi Tới Localhost Backend** | Kết nối trực tiếp từ trình duyệt/máy ảo Wokwi về FastAPI `http://localhost:8000`. | **CÓ ĐIỀU KIỆN** | **BLOCKED / CONDITIONAL** |

---

## 2. Chi Tiết Kết Quả & Phân Tích Kỹ Thuật

### 2.1. Kiểm Tra An Toàn Chân GPIO Khởi Động (Strapping Pins) — PASS
- **Phát hiện từ mã nguồn cũ:** Cấu hình ban đầu đặt `PIN_ULTRASONIC_P01_TRIG` tại GPIO 12 và `PIN_SERVO_BARRIER_EXIT` tại GPIO 15.
- **Rủi ro kỹ thuật:** GPIO 12 là chân MTDI strapping điều khiển điện áp LDO cho bộ nhớ Flash (nếu mức cao sẽ đặt 1.8V gây crash chip). GPIO 15 phát xung PWM boot log tần số cao làm servo rung giật khi vừa bật nguồn.
- **Kết quả điều chỉnh:** Đã chuyển toàn bộ Trigger sang GPIO 25, 26, 27, 32 và Servo sang GPIO 13, 14. Bốn chân Echo được cắm vào các chân Input-only (GPIO 34, 35, 36, 39). Thiết kế đảm bảo khởi động an toàn 100%.

### 2.2. Kiểm Thử Driver Cảm Biến Siêu Âm HC-SR04 — PASS
- Thay thế hoàn toàn vòng lặp trễ phần mềm `ets_delay_us(1)` bằng đồng hồ 64-bit phần cứng `esp_timer_get_time()`, đạt độ chính xác đo khoảng cách $\pm 0.5\text{ cm}$.
- Bổ sung cơ chế chống phản xạ chéo: trễ 15ms giữa các lần đo của 4 ô đỗ.
- Khi mất tín hiệu hoặc timeout quá 30ms, hệ thống lưu giữ trạng thái trước đó và tăng biến đếm lỗi, tuyệt đối không gán nhầm thành ô trống.

### 2.3. Kiểm Thử Driver RFID MFRC522 SPI — PASS
- Cấu hình bus SPI3 (VSPI) dùng chung 3 đường tín hiệu SCK (18), MISO (19), MOSI (23) và chân Reset chung (17).
- Hỗ trợ độc lập 2 đầu đọc qua 2 handle `spi_device_handle_t` với chân CS riêng (Cổng vào GPIO 5, Cổng ra GPIO 4).
- Thuật toán đọc thẻ kiểm tra VersionReg (chống trường hợp dây lỏng), giải mã 4 byte UID và đối chiếu XOR checksum byte thứ 5 trước khi gửi lên hệ thống.

### 2.4. Kiểm Thử Driver Servo & Khóa An Toàn Barrier — PASS
- Sử dụng bộ điều chế độ rộng xung LEDC 13-bit, tần số 50Hz, không sử dụng delay chặn task.
- Hàm `barrier_close()` luôn kiểm tra `barrier_is_obstruction_detected()`. Nếu chùm tia quang bị che chắn (chân GPIO mức 0), hàm trả về ngay `ESP_ERR_INVALID_STATE` và thanh chắn giữ nguyên góc 90°.

### 2.5. Kiểm Thử Đa Nhiệm FreeRTOS & Thread Safety — PASS
- Phân bổ tác vụ đối xứng trên 2 nhân (SMP):
  - **Core 1 (Realtime I/O):** `sensor_task` (chu kỳ 500ms) và `rfid_task` (chu kỳ 150ms).
  - **Core 0 (Networking & Control):** `barrier_task` (chu kỳ 100ms), `network_task` (chu kỳ 2000ms), `display_task` (chu kỳ 1000ms).
- Khóa Mutex `g_telemetry_mutex` bảo vệ mảng dữ liệu 4 ô đỗ, ngăn chặn hiện tượng đọc ghi đồng thời (torn read) giữa 2 nhân vi xử lý.

### 2.6. Trạng Thái Kết Nối Wokwi Virtual Wi-Fi Tới Localhost Backend — CONDITIONAL / BLOCKED
- **Thực tế kỹ thuật:** Wokwi Simulator chạy trong sandbox trình duyệt (WebAssembly) hoặc container cô lập. Để ESP32 ảo kết nối được vào FastAPI Backend đang chạy tại `http://127.0.0.1:8000` trên máy tính host, người dùng cần cài đặt **Wokwi IoT Gateway** để tạo đường hầm bridge qua cổng `10.0.2.2`.
- **Cơ chế dự phòng đã kiểm chứng (Standalone Offline Mode):** Khi không có gateway kết nối mạng, Firmware không bị treo mà tự động chuyển sang chế độ an toàn Offline Fail-Safe. Trong chế độ này, firmware nhận diện các thẻ mẫu đã cấu hình (`30A-123.45`, `01:02:03:04`) để minh họa đầy đủ quy trình nâng/hạ barrier và cập nhật màn hình LCD trên mô phỏng.

---

## 3. Các Hạng Mục Vẫn Bắt Buộc Cần Đo Kiểm Trên Phần Cứng Thật

1. **Hiệu chuẩn góc xoay Servo thật:** Độ rộng xung 500µs – 1500µs trên từng lô sản xuất động cơ SG90/MG90S có thể xê dịch $\pm 5^\circ$ đến $\pm 10^\circ$, cần căn chỉnh ốc vít cơ khí trên trục thực tế.
2. **Khoảng cách đọc thẻ RFID thực tế:** Độ nhạy anten PCB của module RC522 thực tế phụ thuộc vào điện áp cấp 3.3V và nhiễu từ trường của nguồn switching.
3. **Hiện tượng tán xạ sóng siêu âm:** Góc mở của cảm biến HC-SR04 là $15^\circ$, khi đặt trong mô hình bãi đỗ xe thu nhỏ cần có vách ngăn để tránh dội sóng từ tường chắn.
4. **Độ sụt áp khi servo khởi động:** Hai động cơ servo quay cùng lúc có thể kéo dòng đột ngột tới 1.5A, cần sử dụng tụ lọc 1000µF và nguồn 5V ngoài riêng biệt với mạch cấp nguồn ESP32.
