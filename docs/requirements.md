# YÊU CẦU DỰ ÁN — HỆ THỐNG BÃI ĐỖ XE THÔNG MINH (SMART PARKING SYSTEM)

## 1. Giới thiệu tổng quan
Hệ thống Bãi đỗ xe thông minh (Smart Parking System) là giải pháp tích hợp giữa **Hệ thống nhúng (ESP32)**, **Công nghệ nhận dạng vô tuyến (RFID)**, **Internet of Things (IoT - MQTT/HTTP/WebSocket)** và **Thị giác máy tính (Camera AI)** nhằm tự động hoá quy trình quản lý bãi đỗ xe quy mô 4 vị trí (P01, P02, P03, P04) với 1 cổng vào (Entry Gate) và 1 cổng ra (Exit Gate).

Dự án được xây dựng theo kiến trúc module hoá cao, cho phép chạy hoàn toàn ở chế độ mô phỏng (**Simulation / Mock Mode**) khi chưa có phần cứng vật lý, đồng thời sẵn sàng chuyển đổi sang phần cứng thật thông qua các Hardware Abstraction Layers (HAL) rõ ràng.

---

## 2. Các yêu cầu chức năng (Functional Requirements)

### 2.1. Quản lý trạng thái 4 vị trí đỗ xe (Parking Slot Monitoring)
- **FR-01**: Giám sát liên tục 4 vị trí đỗ: `P01`, `P02`, `P03`, `P04`.
- **FR-02**: Phát hiện xe đỗ tại từng vị trí bằng cảm biến siêu âm (HC-SR04).
- **FR-03**: Nhận diện xe tại 4 vị trí đỗ bằng module Camera AI (OpenCV ROI Analysis).
- **FR-04**: Hệ thống phân loại trạng thái của từng vị trí:
  - `EMPTY` (Trống - sẵn sàng đỗ)
  - `OCCUPIED` (Đang có xe đỗ)
  - `RESERVED` (Đã đặt trước - mở rộng)
  - `MISMATCH_ALERT` (Không khớp giữa Camera AI và cảm biến siêu âm)
  - `ERROR` (Lỗi phần cứng/mất tín hiệu)
- **FR-05**: Hiển thị tổng số chỗ trống (`available_slots`) và tỷ lệ lấp đầy theo thời gian thực.

### 2.2. Kiểm soát cổng vào/ra bằng RFID (Access Control)
- **FR-06**: Đọc thẻ RFID (RC522) tại cổng vào (Entry) và cổng ra (Exit).
- **FR-07**: Quy tắc vào (Check-in):
  - Thẻ hợp lệ + Bãi còn chỗ trống (`available_slots > 0`) -> Mở barrier vào, tạo phiên gửi xe (`ParkingSession`), ghi nhận `entry_time`.
  - Thẻ hợp lệ nhưng bãi đã đầy (`available_slots == 0`) -> Từ chối mở barrier, thông báo "PARKING FULL".
  - Thẻ không hợp lệ / chưa đăng ký -> Từ chối mở, cảnh báo âm thanh/đèn.
  - Quét lặp (Double-tap / Anti-passback): Thẻ đang trong trạng thái gửi xe chưa kết thúc không được check-in lần thứ hai.
- **FR-08**: Quy tắc ra (Check-out):
  - Quét thẻ tại cổng ra -> Tìm phiên gửi xe đang hoạt động (`ACTIVE`).
  - Tính thời gian đỗ xe thực tế và chi phí gửi xe dựa trên biểu phí cấu hình.
  - Sau khi xác nhận thanh toán/hợp lệ -> Mở barrier ra, chuyển phiên sang `COMPLETED`, ghi nhận `exit_time`, `fee_paid`.
  - Quét thẻ ra nhưng thẻ chưa từng check-in -> Báo lỗi thẻ chưa vào bãi.

### 2.3. Điều khiển barrier an toàn (Barrier & Safety Control)
- **FR-09**: Barrier điều khiển bằng động cơ Servo (góc mở 90°, góc đóng 0°).
- **FR-10**: Cơ chế an toàn (Safety Interlock): Không được đóng barrier khi cảm biến chùm tia hồng ngoại hoặc siêu âm tại cổng đang phát hiện vật cản.
- **FR-11**: Tự động hạ barrier sau khi xe đã đi qua vùng an toàn (Safety Zone Clear) sau độ trễ trễ định sẵn (ví dụ: 3 giây).

### 2.4. Tính phí và báo cáo doanh thu (Billing & Reporting)
- **FR-12**: Cấu hình biểu phí linh hoạt:
  - Phí theo block thời gian (giờ đầu, các giờ tiếp theo).
  - Phí cố định hoặc lũy tiến.
- **FR-13**: Lưu trữ đầy đủ lịch sử phiên gửi xe: Mã thẻ, thời gian vào, thời gian ra, vị trí đỗ (nếu xác định), tổng tiền, trạng thái thanh toán.
- **FR-14**: Báo cáo tổng doanh thu theo ngày/tháng, số lượt xe vào/ra.

### 2.5. Phát hiện sự sai khác và cảnh báo lỗi (Discrepancy & Health Check)
- **FR-15**: So sánh chéo liên tục giữa dữ liệu cảm biến siêu âm (ESP32) và dữ liệu nhận diện thị giác (Camera AI).
- **FR-16**: Khi trạng thái một ô đỗ khác nhau quá ngưỡng thời gian quy định (ví dụ: > 10 giây) -> Tạo cảnh báo `SENSOR_CAMERA_MISMATCH`.
- **FR-17**: Giám sát trạng thái hoạt động (Heartbeat/Keep-alive) của ESP32 và Camera module. Cảnh báo mất kết nối nếu quá 15 giây không nhận được telemetry.

### 2.6. Chế độ mô phỏng hoàn chỉnh (Full Simulation Support)
- **FR-18**: Mock ESP32 giả lập đọc khoảng cách siêu âm 4 ô đỗ, điều khiển barrier, gửi telemetry qua REST/WebSocket hoặc MQTT.
- **FR-19**: Mock RFID giả lập hành động quẹt thẻ tại cổng vào và cổng ra thông qua Web UI hoặc kịch bản kiểm thử (test scenarios).
- **FR-20**: Mock Camera AI giả lập luồng hình ảnh bãi xe với 4 ROI và tạo dữ liệu phân tích thị giác giả lập.
- **FR-21**: Giao diện hiển thị rõ ràng nhãn **SIMULATION MODE** khi đang kích hoạt chế độ giả lập.

---

## 3. Các yêu cầu phi chức năng (Non-Functional Requirements)

### 3.1. Hiệu năng & Độ trễ
- Độ trễ phản hồi từ khi quẹt thẻ đến khi barrier kích hoạt: < 500ms (ở chế độ thật) và < 100ms (ở chế độ mock).
- Độ trễ cập nhật trạng thái ô đỗ lên Dashboard qua WebSocket: < 1 giây.
- Backend có thể xử lý tối thiểu 50 requests/giây với SQLite (phù hợp cho quy mô lab/đồ án).

### 3.2. Tính sẵn sàng & Phục hồi lỗi
- Dữ liệu phiên gửi xe được ghi tức thời vào cơ sở dữ liệu để phòng ngừa mất điện đột ngột.
- Firmware ESP32 có cơ chế FreeRTOS Task độc lập: Task đọc cảm biến, Task giao tiếp mạng, Task điều khiển barrier; lỗi ở mạng không làm treo servo.

### 3.3. Khả năng bảo trì & Mở rộng
- Thiết kế Module hoá phân tầng: Cấu trúc code sạch (Clean Architecture / Service-Repository pattern ở backend).
- Hỗ trợ thay đổi số lượng ô đỗ từ 4 lên 8 hoặc nhiều hơn chỉ bằng cách cập nhật file cấu hình.
- Chuẩn giao tiếp REST API OpenAPI (Swagger) và chuẩn tin nhắn WebSocket JSON rõ ràng.
