# Kiểm Thử Servo Barrier & Khóa Liên Động An Toàn Trên Wokwi (WOKWI_DEMO_ONLY)

- **Dự án:** SMART PARKING SYSTEM — ESP32 DevKit + Servo SG90 + IR Safety Interlock + RFID RC522
- **Module:** `firmware/esp32/components/barrier/barrier_controller.c`, `network_client.c`, `main.c`
- **Phiên bản:** Phase 3 — Servo Barrier & Safety Interlock Verification
- **Artifact GitHub Actions:**
  - Bản Demo Wokwi: `esp32-wokwi-demo-only` (Chứa `smart_parking_wokwi_demo_merged.bin`)
  - Bản Production: `esp32-firmware-binaries` (Chứa `smart_parking_esp32_merged.bin`)

---

## 1. Bối Cảnh & Mục Tiêu

### Vấn đề thực tế
- Trên môi trường Wokwi Simulator, ESP32 kết nối Wi-Fi ảo `Wokwi-GUEST` thành công.
- Tuy nhiên, hostname Backend `host.wokwi.internal` không thể phân giải DNS nếu máy chủ người dùng không chạy Wokwi IoT Gateway.
- Trong Firmware Chế Độ Phần Cứng Thật (Production Hardware Mode), cơ chế an toàn nghiêm ngặt (Fail-Safe) luôn giữ hai Servo Barrier đóng (`0° CLOSED`) khi không có xác nhận từ Backend. Do đó, người dùng chưa thể kiểm chứng chuyển động của Servo và cảm biến quang an toàn.

### Giải pháp kỹ thuật
Tạo cấu hình build độc lập: **`WOKWI_DEMO_ONLY`** (kích hoạt qua `sdkconfig.demo`).
- **Tách biệt hoàn toàn:** Firmware Production giữ nguyên 100% chính sách an toàn Fail-Safe, từ chối mọi yêu cầu quẹt thẻ khi Backend ngoại tuyến.
- **Xử lý toàn diện 2 tình huống:**
  1. Wi-Fi chưa kết nối (`!g_wifi_connected`).
  2. Wi-Fi đã kết nối nhưng Backend HTTP thất bại (`err != ESP_OK` hoặc status khác 200).
- **Whitelist kiểm soát nghiêm ngặt:** Chỉ có 2 UID thẻ demo hợp lệ mới được phép mở barrier khi Backend không thể kết nối:
  - Cổng Vào (`GATE_ENTRY`): Thẻ Blue Card UID `30:A1:23:45`
  - Cổng Ra (`GATE_EXIT`): Thẻ Blue Card UID `01:02:03:04`
- **Từ chối thẻ lạ:** Bất kỳ thẻ nào khác (ví dụ: Green Card `11:22:33:44`, Red Card `AA:BB:CC:DD`...) đều bị từ chối tuyệt đối.

> [!CAUTION]
> **CẢNH BÁO NGUY HIỂM:**
> Firmware `WOKWI_DEMO_ONLY` chỉ phục vụ mục đích kiểm thử trực quan trên phần mềm mô phỏng Wokwi.
> **TUYỆT ĐỐI KHÔNG NẠP BẢN BUILD NÀY LÊN PHẦN CỨNG ESP32 THẬT TRONG MÔI TRƯỜNG THỰC TẾ.**

---

## 2. Thông Số Kỹ Thuật Điều Khiển Servo & Khóa An Toàn

### 2.1. Điều khiển LEDC PWM (50Hz)
- **Tần số:** 50 Hz (Chu kỳ 20.000 µs).
- **Độ phân giải:** 13-bit (8.192 ticks, mỗi tick tương đương ~2.44 µs).
- **Trạng thái Đóng (0°):** Độ rộng xung 500 µs $\rightarrow$ Giá trị Duty: 205 ticks.
- **Trạng thái Mở (90°):** Độ rộng xung 1.500 µs $\rightarrow$ Giá trị Duty: 614 ticks.
- **Cổng Vào (Entry Servo):** GPIO 13 (`LEDC_CHANNEL_0`, `LEDC_TIMER_0`).
- **Cổng Ra (Exit Servo):** GPIO 14 (`LEDC_CHANNEL_1`, `LEDC_TIMER_0`).

### 2.2. Khóa liên động an toàn (Safety Interlock)
- **Cảm biến an toàn Cổng Vào:** Công tắc trượt / Cảm biến quang `sw_ir_entry` nối GPIO 33 (Active LOW).
- **Cảm biến an toàn Cổng Ra:** Công tắc trượt / Cảm biến quang `sw_ir_exit` nối GPIO 16 (Active LOW).
- **Logic vận hành:**
  1. Khi barrier ở trạng thái MỞ (`90° OPEN`), tác vụ `barrier_task` chạy chu kỳ 100ms.
  2. Nếu không có vật cản (chân cảm biến mức CAO/1), bộ đếm an toàn tích lũy đến 3.000 ms (3 giây) rồi tự động hạ barrier về `0° CLOSED`.
  3. Nếu phát hiện vật cản (chân cảm biến bị kéo xuống THẤP/0 do xe hoặc vật cản che chùm tia):
     - Bộ đếm thời gian an toàn lập tức bị xóa về 0.
     - Hàm `barrier_close()` từ chối thực thi và trả về lỗi `ESP_ERR_INVALID_STATE`.
     - Barrier được duy trì mở ở góc 90° cho đến khi chùm tia quang thông thoáng trở lại.
     - Sau khi vật cản rời đi, hệ thống khởi động lại chu kỳ đếm an toàn 3 giây trước khi hạ barrier.

---

## 3. Quy Trình Kiểm Thử Chi Tiết Trên Wokwi

### Bước 1: Nạp firmware Wokwi Demo
1. Truy cập tab **Actions** trên GitHub Repository.
2. Tải artifact **`esp32-wokwi-demo-only`** từ lần chạy mới nhất.
3. Giải nén và lấy file `smart_parking_wokwi_demo_merged.bin`.
4. Trong Wokwi, cấu hình nạp file bin trên vào ESP32.
5. Bật Serial Monitor (Baud 115200). Quan sát thông điệp khởi động:
   ```text
   W (320) MAIN_APP: ============================================================
   W (325) MAIN_APP:   MODE: WOKWI STANDALONE DEMO ONLY (OFFLINE OVERRIDE ACTIVE)
   W (330) MAIN_APP:   WARNING: DO NOT FLASH THIS FIRMWARE TO PHYSICAL HARDWARE! 
   W (335) MAIN_APP:   Whitelisted Demo Cards: Entry=30:A1:23:45 | Exit=01:02:03:04
   W (340) MAIN_APP: ============================================================
   ```

---

### Bước 2: Kịch bản 1 — Mở Cổng Vào (Entry Gate) Tự Động Đóng Sau 3 Giây
1. Đảm bảo công tắc an toàn `sw_ir_entry` (GPIO 33) đang ở vị trí **OFF** (thông thoáng).
2. Quẹt thẻ Blue Card trên đầu đọc `rfid_entry` (bấm nút Tap hoặc phím `t` khi chọn đầu đọc).
3. **Quan sát kết quả mong đợi:**
   - Serial Monitor:
     ```text
     I (14520) MFRC522_RFID: [ENTRY RFID] Raw UID: 30 A1 23 45 F7 | FIFO_len=5, RxLastBits=0, ErrorReg=0x00, ComIrq=0x20 | BCC calc=0xF7, recv=0xF7
     I (14530) MAIN_APP: >>> ENTRY TAP: Card UID = 30:A1:23:45 <<<
     W (14535) NET_CLIENT: [WOKWI_DEMO_ONLY] Whitelisted card allowed (Backend HTTP unreachable): 30:A1:23:45
     I (14540) MAIN_APP: Entry Granted! Raising barrier.
     I (14545) BARRIER_LEDC: Gate ENTRY: Setting servo to 90° OPEN.
     ```
   - Servo `servo_entry` quay từ **0° lên 90°**.
   - Màn hình LCD hiển thị dòng 2: `WELCOME! OPEN` $\rightarrow$ `ENTRY GATE OPEN`.
   - Sau đúng 3 giây không có vật cản:
     ```text
     I (17550) BARRIER_LEDC: Gate ENTRY: Path is clear. Setting servo to 0° CLOSED.
     ```
   - Servo `servo_entry` quay trở lại **0°**.

---

### Bước 3: Kịch bản 2 — Mở Cổng Ra (Exit Gate) Tự Động Đóng Sau 3 Giây
1. Đảm bảo công tắc an toàn `sw_ir_exit` (GPIO 16) đang ở vị trí **OFF**.
2. Quẹt thẻ trên đầu đọc `rfid_exit` (UID `01:02:03:04`).
3. **Quan sát kết quả mong đợi:**
   - Serial Monitor:
     ```text
     I (25100) MAIN_APP: >>> EXIT TAP: Card UID = 01:02:03:04 <<<
     W (25105) NET_CLIENT: [WOKWI_DEMO_ONLY] Whitelisted card allowed (Backend HTTP unreachable): 01:02:03:04
     I (25110) MAIN_APP: Exit Granted! Raising barrier.
     I (25115) BARRIER_LEDC: Gate EXIT: Setting servo to 90° OPEN.
     ```
   - Servo `servo_exit` quay lên **90°**.
   - Sau 3 giây thông thoáng, `servo_exit` quay về **0°**.

---

### Bước 4: Kịch bản 3 — Khóa Liên Động An Toàn (Safety Interlock Khi Có Vật Cản)
1. Quẹt thẻ `30:A1:23:45` tại Cổng Vào để mở barrier lên 90°.
2. **Trong vòng 3 giây trước khi barrier hạ xuống**, gạt công tắc `sw_ir_entry` (GPIO 33) sang vị trí **ON** (mô phỏng xe đang nằm dưới barrier).
3. **Quan sát kết quả mong đợi:**
   - Serial Monitor:
     ```text
     W (16200) MAIN_APP: Gate ENTRY: Obstruction detected (IR Beam blocked)! SAFETY INTERLOCK ACTIVE: Barrier kept OPEN.
     ```
   - Màn hình LCD cập nhật: `ENTRY OBSTRUCT`.
   - **Barrier duy trì mở ở 90°, tuyệt đối KHÔNG đóng lại** cho dù chờ 10 giây, 20 giây hay lâu hơn.
4. Gạt công tắc `sw_ir_entry` trở lại vị trí **OFF** (mô phỏng xe đã đi qua hết).
   - Serial Monitor:
     ```text
     I (28400) MAIN_APP: Gate ENTRY: Obstruction cleared. Resuming 3s safety close countdown.
     ```
   - Màn hình LCD cập nhật: `ENTRY GATE OPEN`.
   - Đếm đúng 3 giây sau khi thông thoáng, barrier hạ về **0° CLOSED**:
     ```text
     I (31450) BARRIER_LEDC: Gate ENTRY: Path is clear. Setting servo to 0° CLOSED.
     ```

---

### Bước 5: Kịch bản 4 — Thẻ Lạ Không Nằm Trong Whitelist
1. Trong Wokwi, đổi thẻ quẹt sang thẻ khác (ví dụ: Green Card UID `11:22:33:44`).
2. Quẹt thẻ tại Cổng Vào hoặc Cổng Ra.
3. **Quan sát kết quả mong đợi:**
   - Serial Monitor:
     ```text
     W (40100) NET_CLIENT: [WOKWI_DEMO_ONLY] Non-whitelisted card rejected (Backend HTTP unreachable): 11:22:33:44
     W (40105) MAIN_APP: Entry Denied: Demo Denied - Not Whitelisted
     ```
   - Màn hình LCD hiển thị: `ACCESS DENIED`.
   - **Servo barrier KHÔNG di chuyển (vẫn ở 0° CLOSED)**.

---

## 4. Bảng Tổng Hợp Kiểm Thử & Nghiệm Thu

| STT | Kịch Bản Kiểm Thử | Tiêu Chuẩn Đạt (Expected) | Kết Quả Thực Tế | Trạng Thái |
| :-- | :--- | :--- | :--- | :--- |
| **01** | **Regression Pytest Suite** | 23/23 tests backend & vision đạt | 23 passed in 4.70s | **PASS** ✅ |
| **02** | **Frontend Production Build** | Vite build thành công không lỗi TypeScript | 2065 modules transformed | **PASS** ✅ |
| **03** | **ESP-IDF CI Build kép** | Sinh độc lập cả 2 artifact: production & demo | Build cả 2 thành công trên GitHub Actions | **PASS** ✅ |
| **04** | **Phân tách Artifacts** | Artifact `esp32-wokwi-demo-only` tách biệt `esp32-firmware-binaries` | 2 artifact riêng biệt trên GitHub Actions | **PASS** ✅ |
| **05** | **Wokwi Runtime Servo & Interlock** | Người dùng nạp file demo bin và quan sát chuyển động Servo + Switch | Chờ kiểm chứng thực tế trong Wokwi | **NOT VERIFIED** ⚠️ |

> [!NOTE]
> Trạng thái kiểm chứng mô phỏng runtime trên Wokwi được ghi nhận trung thực là **NOT VERIFIED** cho đến khi người dùng nạp file `smart_parking_wokwi_demo_merged.bin` và xác nhận kết quả Serial Monitor thực tế.
