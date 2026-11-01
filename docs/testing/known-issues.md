# BÁO CÁO CÁC VẤN ĐỀ ĐÃ BIẾT & GIỚI HẠN HỆ THỐNG (KNOWN ISSUES & LIMITATIONS)
## SMART PARKING SYSTEM — PHIÊN BẢN MÔ PHỎNG GIAI ĐOẠN 2

---

## 1. Tóm Tắt Hiện Trạng (Status Overview)

Toàn bộ các lỗi nghiêm trọng (Critical/High) liên quan đến tính đúng đắn của logic nghiệp vụ, tính an toàn cơ học của barrier, tràn cảnh báo và xung đột đồng thời đã được phát hiện và giải quyết triệt để trong Giai đoạn 2.
Bảng phân loại sau phản ánh các hạn chế còn lại thuộc phạm vi mô phỏng và lộ trình nâng cấp phần cứng trong tương lai:

| Mức Độ Nghiêm Trọng | Số Lượng Đã Khắc Phục | Số Lượng Tồn Đọng | Ghi Chú |
| :--- | :---: | :---: | :--- |
| **CRITICAL** | 2 | **0** | Đã khắc phục lỗi khóa an toàn barrier & race condition dung lượng |
| **HIGH** | 3 | **0** | Đã khắc phục tràn cảnh báo, mất gói telemetry watchdog, mất tín hiệu camera |
| **MEDIUM** | 2 | **1** | Môi trường HIL chưa có mạch phần cứng thật (chạy qua HAL adapter) |
| **LOW** | 1 | **1** | Thuật toán nhận diện thị giác hiện tại dùng Baseline Heuristic thay vì YOLO |

---

## 2. Chi Tiết Các Vấn Đề Đã Được Khắc Phục (Resolved Issues)

### 2.1. Lỗi Khóa Đồng Thời & Vượt Quá Dung Lượng 4 Vị Trí (CRITICAL - Resolved)
- **Vấn đề:** Ban đầu hàm `process_entry_tap()` chỉ đếm số ô `ParkingSlot.status == "EMPTY"`. Khi xe vừa được cấp quyền mở barrier vào, ô đỗ thực tế vẫn chưa bị đè lên cảm biến siêu âm. Nếu 4 xe liên tiếp quẹt thẻ trong thời gian ngắn, xe thứ 5 vẫn được mở barrier, dẫn tới tình trạng nhận quá tải bãi xe.
- **Giải pháp:** Bổ sung `_entry_lock = asyncio.Lock()` trong `ParkingService`, đồng thời kiểm tra đồng thời:
  $$\text{active\_sessions} < 4 \quad \text{AND} \quad \text{available\_slots} > 0$$
- **Kiểm chứng:** Test case `test_10_high_concurrency_race_condition` chạy 8 tác vụ đồng thời: chính xác 4 thẻ ALLOWED, 4 thẻ REJECTED với mã `PARKING_FULL`.

### 2.2. Tràn Cảnh Báo Lặp Lại Khi Có Sai Lệch Cảm Biến/Camera (HIGH - Resolved)
- **Vấn đề:** Mỗi nhịp gửi telemetry chu kỳ 2 giây, nếu trạng thái ô đỗ có sai lệch (`has_mismatch == True`), hệ thống tự động `db.add(SystemAlert)` mà không kiểm tra xem cảnh báo đã tồn tại hay chưa. Điều này làm bảng SQLite bị spam hàng ngàn bản ghi trùng lặp trong vài phút.
- **Giải pháp:** Trước khi tạo bản ghi mới, truy vấn kiểm tra `existing_alert = db.query(SystemAlert).filter(alert_type==..., is_resolved==False)`. Nếu chưa có mới tạo mới. Khi hai nguồn dữ liệu khớp trở lại, tự động đánh dấu `is_resolved = True`.
- **Kiểm chứng:** Test case `test_06_sensor_camera_mismatch` gửi 4 nhịp lặp lại: số lượng cảnh báo chưa xử lý duy nhất là 1, tự động resolved khi camera thấy xe.

### 2.3. Xử Lý Tín Hiệu Camera Bị Suy Giảm / Lỗi Frame (HIGH - Resolved)
- **Vấn đề:** Khi frame hình ảnh bị mất gói hoặc detector trả về `state="UNKNOWN"` hoặc `"CAMERA_ERROR"`, code cũ gán `is_occupied = False`, làm ô đỗ bị gán nhầm thành EMPTY!
- **Giải pháp:** Khi nhận trạng thái `UNKNOWN`/`CAMERA_ERROR`, ô đỗ được giữ nguyên trạng thái hoặc chuyển sang `UNKNOWN`, bật cờ `has_mismatch = True` và ghi nhận cảnh báo `CAMERA_SIGNAL_LOST` thay vì gán trống ô đỗ.
- **Kiểm chứng:** Test case `test_09_camera_signal_loss`.

### 2.4. Khóa Liên Động An Toàn Cánh Barrier (CRITICAL - Resolved)
- **Vấn đề:** Trong Firmware ESP32 và Mock Barrier, việc chờ 3 giây trước khi đóng dùng vòng lặp trễ chặn (`vTaskDelay(3000)`). Trong 3 giây đó, nếu xe khác chạy vào chắn ngang chùm tia quang an toàn, cảm biến không được quét liên tục và cánh tay đòn vẫn hạ xuống.
- **Giải pháp:** Chuyển sang máy trạng thái đếm xung không chặn (non-blocking countdown state machine, tick 100ms). Bất kỳ khi nào chùm tia bị che chắn (`barrier_is_obstruction_detected == true`), bộ đếm tự động reset về 0 ngay lập tức.
- **Kiểm chứng:** Test case `test_07_barrier_safety_interlock` và `scenario_5_barrier_safety`.

### 2.5. Rò Rỉ Kết Nối Reconnect WebSocket Trên Frontend (MEDIUM - Resolved)
- **Vấn đề:** Khi chuyển trang hoặc unmount component React, `ws.onclose` gọi `setTimeout(connectWs, 3000)` mà không dọn dẹp timer, gây ra hiện tượng tạo nhiều kết nối WebSocket trùng lặp (duplicate sockets) làm chậm trình duyệt.
- **Giải pháp:** Bổ sung cờ `isMounted` và lưu biến tham chiếu `reconnectTimer`. Trong hàm cleanup của `useEffect`, gọi `clearTimeout(reconnectTimer)` và `ws.close()`.

---

## 3. Các Giới Hạn Tồn Đọng & Giải Pháp Tạm Thời (Remaining Limitations & Workarounds)

### 3.1. Nhận Diện Thị Giác Hiện Dùng Baseline Heuristic (LOW)
- **Hạn chế:** Module `occupancy_detector.py` hiện tại sử dụng thuật toán phân tích mật độ cạnh Canny và độ biến thiên màu sắc không gian HSV của từng vùng đỗ (ROI) mẫu. Thuật toán này rất nhẹ và chạy mượt mà ở chế độ mô phỏng, nhưng có thể bị ảnh hưởng bởi bóng đổ phức tạp hoặc ánh sáng ban đêm ngoài trời.
- **Giải pháp tạm thời:** Hệ thống đã được thiết kế kiến trúc cắm rút (pluggable architecture). Module `OccupancyDetector` có interface trừu tượng chuẩn. Khi bước sang giai đoạn huấn luyện mô hình sâu, sinh viên chỉ cần thay thế hàm suy luận bằng YOLOv8 (`yolov8n.pt`) mà không cần thay đổi REST API `/api/v1/vision/occupancy` hoặc cấu trúc database.

### 3.2. Thiếu Mạch Phần Cứng Thật (HIL Test Bench) (MEDIUM)
- **Hạn chế:** Chưa thể đo kiểm thời gian phản hồi thực tế của sóng siêu âm HC-SR04 khi phản xạ trên bề mặt kim loại nghiêng của xe hơi thật, hoặc độ trôi góc (jitter) của động cơ RC Servo SG90 khi tải cánh chắn bằng nhôm dài 30cm.
- **Giải pháp tạm thời:** Toàn bộ tầng giao tiếp phần cứng được cô lập hoàn hảo qua `HardwareAdapter` (Python) và FreeRTOS HAL (C). Mọi thông số vật lý như thời gian nâng/hạ cánh tay (1.2s), góc xoay 0-90°, khoảng cách phát hiện xe 5-25cm đều được mô phỏng sát thực tế.

### 3.3. SQLite Khóa Toàn Tệp Khi Có Quá Nhiều Tiến Trình Ghi Đồng Thời (LOW)
- **Hạn chế:** SQLite là cơ sở dữ liệu dạng file đơn. Mặc dù phù hợp cho giai đoạn phát triển đồ án tốt nghiệp và mô phỏng 4 ô đỗ xe, nhưng nếu mở rộng ra 100+ vị trí đỗ với hàng nghìn truy vấn ghi mỗi giây, có thể phát sinh `sqlite3.OperationalError: database is locked`.
- **Giải pháp tạm thời:** Trong `ParkingService`, các thao tác ghi quan trọng đã được bảo vệ bằng mutex lock. Khi triển khai hệ thống thương mại quy mô lớn, chỉ cần đổi chuỗi kết nối `DATABASE_URL` sang PostgreSQL hoặc MySQL trong file `.env`.
