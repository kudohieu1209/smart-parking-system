# KẾ HOẠCH KIỂM THỬ TÍCH HỢP HỆ THỐNG — PHASE 3.5
## WOKWI ESP32 ↔ FASTAPI BACKEND ↔ REACT DASHBOARD REALTIME INTEGRATION

**Dự án:** Smart Parking System — ESP32 + RFID + Camera AI + IoT  
**Mục tiêu:** Tích hợp thời gian thực giữa vi điều khiển ESP32 chạy trên mô phỏng Wokwi với REST API Backend FastAPI và Giao diện Dashboard React qua WebSocket.  
**Phiên bản kiểm thử:** Phase 3.5  
**Quy tắc thẩm định:** 
- Phân tách rõ ràng giữa kiểm thử phần mềm tự động (Automated Regression Tests) và kiểm chứng thời gian thực trên Wokwi (Hardware Simulator Runtime).
- Trạng thái mô phỏng Wokwi runtime chỉ được xác nhận khi có log thực tế; các kịch bản chưa thể chạy trực tiếp do môi trường được đánh dấu `NOT VERIFIED`.

---

## 1. Danh sách 15 Kịch bản Kiểm thử Tích hợp (Integration Test Matrix)

| Test ID | Kịch bản kiểm thử (Scenario) | Điều kiện & Dữ liệu đầu vào (Input) | Kết quả kỳ vọng (Expected Output) | Trạng thái xác minh |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Khởi động ESP32 & Kết nối mạng Wi-Fi Station | Khởi động firmware; AP `Wokwi-GUEST` sẵn sàng (hoặc Wokwi IoT Gateway). | ESP32 nhận IP nội bộ từ DHCP, log Serial `Wi-Fi connected! Got IP: x.x.x.x`, cờ `g_wifi_connected = true`. | **NOT VERIFIED** (Chờ người dùng chạy Wokwi) |
| **TC-02** | Đồng bộ số liệu cảm biến siêu âm 4 ô đỗ (Telemetry Ingestion) | 4 cảm biến HC-SR04 đo khoảng cách (P01: 18cm, P02: 120cm, P03: 120cm, P04: 120cm). | ESP32 gửi `POST /api/v1/telemetry/sensors` định kỳ 2s. FastAPI trả về HTTP 200, cập nhật DB SQLite ô P01 `sensor_occupied = true`. | **PASS** (Unit/Mock test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-03** | Phát sóng trạng thái ô đỗ qua WebSocket | Telemetry ô đỗ cập nhật trong CSDL. | Backend phát sóng sự kiện `SLOTS_BULK_UPDATE` tới tất cả WebSocket client kết nối tại `/ws`. | **PASS** (Automated Backend test) |
| **TC-04** | Hiển thị Realtime trạng thái bãi trên React Dashboard | Nhận sự kiện `SLOTS_BULK_UPDATE` qua WebSocket. | Giao diện Web lập tức chuyển đổi card P01 sang màu đỏ (OCCUPIED), số chỗ trống giảm từ 4 xuống 3 không cần reload trang. | **PASS** (Frontend Build & API test) |
| **TC-05** | Quẹt thẻ RFID hợp lệ tại Cổng Vào (Entry Tap) | Quẹt thẻ UID `30:A1:23:45` (Đoàn Minh Đức, biển số `30A-123.45`) tại đầu đọc RC522 Cổng Vào. | ESP32 gửi `POST /api/v1/gate/entry-tap`. Backend xác thực thành công, tạo `ACTIVE` session, trả về `status: ALLOWED`, `action: OPEN_BARRIER`. | **PASS** (Automated API test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-06** | Mở Servo Barrier Cổng Vào & Phản hồi Telemetry | ESP32 nhận phản hồi `ALLOWED` & `OPEN_BARRIER` từ Backend. | ESP32 quay servo Cổng Vào lên 90 độ, hiển thị LCD `WELCOME! OPEN`, và gửi `POST /api/v1/gate/barrier-state` (`ENTRY`, `OPEN`, `angle: 90`). | **PASS** (Firmware code & HAL API test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-07** | Phản ánh trạng thái Barrier Cổng Vào trên Dashboard | Backend nhận `POST /gate/barrier-state` từ ESP32 và phát sóng `BARRIER_UPDATE`. | React Dashboard cập nhật đồ họa cánh barie Cổng Vào từ góc 0 độ sang 90 độ (Mở). | **PASS** (Frontend WebSocket hook) |
| **TC-08** | Xe di chuyển vào ô đỗ P01 & Cập nhật LCD | Xe đi qua barie vào ô P01, khoảng cách HC-SR04 P01 hạ xuống < 25cm. | Màn hình LCD 1602 chuyển hiển thị `P:3 EMPTY`, Backend cập nhật trạng thái ô đỗ. | **NOT VERIFIED** (Chờ Wokwi runtime) |
| **TC-09** | Khóa liên động an toàn: Phát hiện vật cản khi barrier đang mở (Safety Interlock Active) | Gạt switch cảm biến an toàn quang Cổng Vào sang mức LOW (có vật cản/xe đang dừng dưới barie). | ESP32 phát hiện vật cản, gửi `POST /api/v1/gate/safety-sensor` (`ENTRY`, `has_obstruction: true`). Bộ đếm đóng 3s bị reset về 0, barie giữ nguyên 90 độ. | **PASS** (Automated Safety Test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-10** | Khóa liên động an toàn: Thông thoáng vật cản & Tự động đóng barie (Safety Auto-Close) | Gạt switch cảm biến quang về HIGH (hết vật cản). | ESP32 gửi `POST /api/v1/gate/safety-sensor` (`has_obstruction: false`), đếm đủ 3000ms liên tục thông thoáng, servo quay về 0 độ (Đóng). | **PASS** (Firmware timer logic) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-11** | Cập nhật đóng Barrier Cổng Vào trên Dashboard | ESP32 đóng servo xong, gửi `POST /api/v1/gate/barrier-state` (`ENTRY`, `CLOSED`, `angle: 0`). | Backend phát sóng `BARRIER_UPDATE`, Dashboard hạ cánh barie Cổng Vào về góc nằm ngang 0 độ. | **PASS** (Automated API test) |
| **TC-12** | Quẹt thẻ RFID cùng xe tại Cổng Ra (Single Turnaround Exit Tap) | Quẹt đúng thẻ `30:A1:23:45` tại đầu đọc RC522 Cổng Ra (sau khi cấu hình `rfid_exit` cùng UID). | ESP32 gửi `POST /api/v1/gate/exit-tap`. Backend tìm thấy phiên `ACTIVE`, tính thời gian & phí gửi, chuyển trạng thái `COMPLETED`, trả về `ALLOWED` & `OPEN_BARRIER`. | **PASS** (Automated API test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-13** | Mở Servo Barrier Cổng Ra & Phản hồi Telemetry | ESP32 nhận phản hồi `ALLOWED` & `OPEN_BARRIER` cho Cổng Ra. | ESP32 quay servo Cổng Ra lên 90 độ, LCD hiển thị `GOODBYE! OPEN`, gửi `POST /gate/barrier-state` (`EXIT`, `OPEN`, `angle: 90`), Dashboard mở barie Cổng Ra. | **PASS** (Automated API test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-14** | Xe rời bãi & Ô đỗ trở về trạng thái trống | Cảm biến HC-SR04 P01 tăng khoảng cách lên > 25cm (ví dụ 120cm). | Telemetry gửi lên Backend, ô P01 chuyển `EMPTY` (màu xanh lá trên Web), màn hình LCD cập nhật `P:4 EMPTY`. | **PASS** (Automated Slot test) / **NOT VERIFIED** (Wokwi runtime) |
| **TC-15** | Kiểm tra Fail-Safe: Quẹt thẻ chưa đăng ký / Thẻ bị khóa | Quẹt thẻ không xác định (VD: `FF:EE:DD:CC`) hoặc thẻ đã bị khóa (`is_active = false`). | Backend trả về `status: REJECTED`, `action: KEEP_CLOSED`. ESP32 giữ nguyên servo 0 độ, LCD báo `ACCESS DENIED`, cảnh báo âm thanh/log. | **PASS** (Automated Security test) |

---

## 2. Quy trình thiết lập kiểm thử Single Turnaround trên Wokwi

Để kiểm thử trọn vẹn 1 xe vào rồi ra (1 chu kỳ đóng/mở phiên hoàn chỉnh):
1. Mở file `firmware/esp32/diagram.json`.
2. Định vị linh kiện `rfid_exit`:
   ```json
   {
     "type": "board-mfrc522",
     "id": "rfid_exit",
     "top": 240,
     "left": -60,
     "attrs": { "uid": "30:A1:23:45" }
   }
   ```
3. Đổi `"attrs": { "uid": "30:A1:23:45" }` để cả đầu đọc vào và đầu đọc ra đều đọc cùng thẻ của Đoàn Minh Đức (`30A-123.45`).
4. Khởi chạy mô phỏng:
   - Click thẻ trên `rfid_entry`: Barie Vào mở, Dashboard ghi nhận phiên mới.
   - Chỉnh HC-SR04 `ultrasonic1` xuống 15cm: Ô P01 chuyển đỏ.
   - Click thẻ trên `rfid_exit`: Barie Ra mở, Dashboard tính tiền và hoàn tất phiên.
   - Chỉnh HC-SR04 `ultrasonic1` lên 120cm: Ô P01 chuyển xanh.
