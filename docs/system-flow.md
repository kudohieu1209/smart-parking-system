# QUY TRÌNH HOẠT ĐỘNG HỆ THỐNG — SYSTEM FLOW

## 1. Quy trình xe vào bãi (Vehicle Entry Flow)

Quy trình diễn ra khi xe tiến đến cổng vào và tài xế quét thẻ RFID:

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Tài xế / Xe
    participant RFID as RFID Reader (Entry)
    participant ESP as ESP32 / Mock ESP
    participant Backend as FastAPI Backend
    participant DB as SQLite DB
    participant UI as Frontend Dashboard

    Driver ->> RFID: Quét thẻ RFID (Tap Card)
    RFID ->> ESP: Gửi card_uid (VD: "TAG-9A3B12")
    ESP ->> Backend: POST /api/v1/gate/entry-tap {card_uid, gate_id: "ENTRY"}
    Backend ->> DB: Kiểm tra thẻ và phiên hoạt động
    
    alt Thẻ không hợp lệ
        Backend -->> ESP: {status: "REJECTED", reason: "CARD_UNKNOWN"}
        ESP ->> Driver: Cảnh báo còi / LED Đỏ
    else Thẻ hợp lệ nhưng bãi đã đầy (available_slots == 0)
        Backend -->> ESP: {status: "REJECTED", reason: "PARKING_FULL"}
        ESP ->> Driver: Thông báo bãi đầy trên màn hình LCD
    else Thẻ đang có phiên ACTIVE (Anti-passback)
        Backend -->> ESP: {status: "REJECTED", reason: "CARD_ALREADY_IN_USE"}
        ESP ->> Driver: Cảnh báo thẻ chưa check-out
    else Hợp lệ và còn chỗ trống
        Backend ->> DB: Tạo mới ParkingSession (status: "ACTIVE", entry_time: NOW)
        Backend -->> ESP: {status: "ALLOWED", barrier: "OPEN", session_id: 101}
        Backend ->> UI: WebSocket: session_created event + available_slots updated
        ESP ->> Driver: Servo quay 90° (Barrier mở), LED Xanh
        Driver ->> ESP: Xe đi qua cổng an toàn (Safety sensor clear)
        ESP ->> ESP: Đếm trễ 3s an toàn -> Servo quay về 0° (Barrier đóng)
        ESP ->> Backend: POST /api/v1/gate/barrier-status {gate_id: "ENTRY", state: "CLOSED"}
    end
```

---

## 2. Quy trình xe đỗ vào ô và đồng bộ trạng thái (Slot Occupancy Flow)

Khi xe di chuyển vào vị trí đỗ P01 - P04:

```mermaid
sequenceDiagram
    autonumber
    actor Car as Xe vào ô P01
    participant Sensor as Ultrasonic HC-SR04
    participant Cam as Camera AI (OpenCV)
    participant Backend as FastAPI Backend
    participant UI as Frontend Dashboard

    Car ->> Sensor: Khoảng cách giảm < 30 cm
    Sensor ->> Backend: POST /api/v1/telemetry/slots {P01: {occupied: true, distance: 18.5}}
    
    Car ->> Cam: Xe xuất hiện trong ROI P01
    Cam ->> Backend: POST /api/v1/vision/occupancy {P01: {state: "OCCUPIED", confidence: 0.94}}
    
    Backend ->> Backend: Kiểm tra tính nhất quán (Sensor vs Camera)
    alt Khớp dữ liệu (Sensor == OCCUPIED && Camera == OCCUPIED)
        Backend ->> Backend: Cập nhật SlotStatus P01 = OCCUPIED
        Backend ->> UI: WebSocket: slot_updated {slot_id: "P01", status: "OCCUPIED"}
    else Không khớp kéo dài (> 5 giây)
        Backend ->> Backend: Cập nhật SlotStatus P01 = MISMATCH
        Backend ->> UI: WebSocket: mismatch_alert {slot_id: "P01", sensor: true, camera: false}
    end
```

---

## 3. Quy trình xe ra bãi và tính phí (Vehicle Exit Flow)

Khi tài xế rời ô đỗ và tiến đến cổng ra:

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Tài xế / Xe
    participant RFID as RFID Reader (Exit)
    participant ESP as ESP32 / Mock ESP
    participant Backend as FastAPI Backend
    participant DB as SQLite DB
    participant UI as Frontend Dashboard

    Driver ->> RFID: Quét thẻ RFID tại cổng ra
    RFID ->> ESP: Gửi card_uid
    ESP ->> Backend: POST /api/v1/gate/exit-tap {card_uid, gate_id: "EXIT"}
    
    Backend ->> DB: Truy vấn ParkingSession với card_uid đang "ACTIVE"
    alt Không tìm thấy phiên gửi xe
        Backend -->> ESP: {status: "REJECTED", reason: "NO_ACTIVE_SESSION"}
        ESP ->> Driver: Báo lỗi thẻ chưa check-in
    else Tìm thấy phiên gửi xe hợp lệ
        Backend ->> Backend: Tính thời gian: duration = exit_time - entry_time
        Backend ->> Backend: Tính phí: fee = calculate_fee(duration, pricing_rule)
        Backend ->> DB: Cập nhật session (status: "COMPLETED", exit_time: NOW, fee: fee)
        Backend -->> ESP: {status: "ALLOWED", barrier: "OPEN", fee: fee, duration_minutes: 45}
        Backend ->> UI: WebSocket: session_completed event + revenue update
        ESP ->> Driver: Hiển thị tiền cước trên LCD, Servo quay 90° mở barrier
        Driver ->> ESP: Xe đi qua cổng an toàn
        ESP ->> ESP: Đóng barrier sau 3s
        ESP ->> Backend: POST /api/v1/gate/barrier-status {gate_id: "EXIT", state: "CLOSED"}
    end
```

---

## 4. Xử lý các trường hợp ngoại lệ (Edge Cases)

1. **Bãi đầy (Available slots = 0):**
   - Đèn báo cổng chuyển đỏ.
   - Thẻ quét bị từ chối với lý do rõ ràng.
   - Giao diện Dashboard hiển thị cảnh báo bãi đầy.
2. **Kẹt barrier (Vật cản trong khi đang hạ):**
   - Cảm biến hồng ngoại/khoảng cách phát hiện vật cản tại cổng -> Lập tức đảo chiều Servo mở lại 90°.
   - Gửi cảnh báo `BARRIER_OBSTRUCTION_DETECTED` về Backend.
3. **Mất kết nối ESP32 hoặc Camera AI:**
   - Backend chạy định kỳ kiểm tra Heartbeat (mỗi 10 giây).
   - Nếu quá 15 giây không nhận telemetry -> chuyển trạng thái thiết bị sang `OFFLINE` trên Dashboard.
4. **Mất nguồn hoặc reset ESP32 giữa chừng:**
   - ESP32 là stateless đối với phiên gửi xe; toàn bộ phiên được lưu trữ an toàn trong Database của Backend. Khi ESP32 khởi động lại, nó tiếp tục đọc cảm biến bình thường mà không làm mất phiên xe.
