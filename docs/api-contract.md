# ĐẶC TẢ GIAO DIỆN API & WEBSOCKET — API CONTRACT

Hệ thống giao tiếp thông qua RESTful HTTP API (chuẩn JSON) cho các yêu cầu điều khiển/truy vấn và WebSocket cho truyền phát sự kiện thời gian thực.

Base URL: `http://localhost:8000/api/v1`  
WebSocket URL: `ws://localhost:8000/ws/live`

---

## 1. REST API Endpoints

### 1.1. Parking Slots (Vị trí đỗ xe)

#### `GET /api/v1/slots`
Lấy danh sách và trạng thái hiện tại của tất cả các vị trí đỗ.
- **Response (200 OK):**
```json
{
  "total_slots": 4,
  "available_slots": 2,
  "slots": [
    {
      "slot_id": "P01",
      "status": "OCCUPIED",
      "sensor_distance_cm": 15.2,
      "sensor_occupied": true,
      "camera_occupied": true,
      "camera_confidence": 0.95,
      "has_mismatch": false,
      "updated_at": "2026-11-01T07:30:00Z"
    },
    {
      "slot_id": "P02",
      "status": "EMPTY",
      "sensor_distance_cm": 120.0,
      "sensor_occupied": false,
      "camera_occupied": false,
      "camera_confidence": 0.98,
      "has_mismatch": false,
      "updated_at": "2026-11-01T07:30:00Z"
    }
  ]
}
```

#### `POST /api/v1/slots/{slot_id}/override`
Điều khiển gán đè trạng thái thủ công hoặc dùng cho Simulator.
- **Request Body:**
```json
{
  "status": "OCCUPIED",
  "reason": "MANUAL_SIMULATION_TRIGGER"
}
```

---

### 1.2. Gate & RFID Control (Kiểm soát cổng & Thẻ)

#### `POST /api/v1/gate/entry-tap`
Gửi sự kiện quẹt thẻ tại cổng vào.
- **Request Body:**
```json
{
  "card_uid": "TAG-8F2B10",
  "gate_id": "ENTRY"
}
```
- **Response (200 OK):**
```json
{
  "status": "ALLOWED",
  "action": "OPEN_BARRIER",
  "message": "Welcome to Smart Parking",
  "session": {
    "session_id": 101,
    "card_uid": "TAG-8F2B10",
    "vehicle_plate": "30A-99999",
    "entry_time": "2026-11-01T07:30:00Z",
    "status": "ACTIVE"
  }
}
```
- **Error Response (400 Bad Request / 409 Conflict):**
```json
{
  "status": "REJECTED",
  "reason": "PARKING_FULL",
  "message": "Cannot check in: No available parking slots."
}
```

#### `POST /api/v1/gate/exit-tap`
Gửi sự kiện quẹt thẻ tại cổng ra.
- **Request Body:**
```json
{
  "card_uid": "TAG-8F2B10",
  "gate_id": "EXIT"
}
```
- **Response (200 OK):**
```json
{
  "status": "ALLOWED",
  "action": "OPEN_BARRIER",
  "message": "Check-out successful",
  "session": {
    "session_id": 101,
    "card_uid": "TAG-8F2B10",
    "vehicle_plate": "30A-99999",
    "entry_time": "2026-11-01T07:00:00Z",
    "exit_time": "2026-11-01T07:30:00Z",
    "duration_minutes": 30,
    "fee_amount": 10000,
    "status": "COMPLETED"
  }
}
```

#### `POST /api/v1/gate/barrier-state`
ESP32 hoặc Simulator cập nhật trạng thái cánh barrier.
- **Request Body:**
```json
{
  "gate_id": "ENTRY",
  "state": "CLOSED",
  "angle": 0
}
```

---

### 1.3. Telemetry (Cảm biến & Camera AI)

#### `POST /api/v1/telemetry/sensors`
ESP32 gửi số liệu cảm biến siêu âm của 4 ô.
- **Request Body:**
```json
{
  "device_id": "ESP32_CORE_01",
  "readings": [
    {"slot_id": "P01", "distance_cm": 18.5, "occupied": true},
    {"slot_id": "P02", "distance_cm": 115.0, "occupied": false},
    {"slot_id": "P03", "distance_cm": 118.2, "occupied": false},
    {"slot_id": "P04", "distance_cm": 22.1, "occupied": true}
  ]
}
```

#### `POST /api/v1/vision/occupancy`
Camera AI gửi kết quả nhận dạng từ 4 ROI.
- **Request Body:**
```json
{
  "camera_id": "CAM_MAIN_01",
  "slots": [
    {"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.96},
    {"slot_id": "P02", "state": "EMPTY", "confidence": 0.98},
    {"slot_id": "P03", "state": "EMPTY", "confidence": 0.97},
    {"slot_id": "P04", "state": "OCCUPIED", "confidence": 0.92}
  ]
}
```

---

### 1.4. Quản lý Thẻ & Phiên (Cards & Sessions)

#### `GET /api/v1/cards`
Danh sách thẻ RFID đã đăng ký trong hệ thống.

#### `POST /api/v1/cards`
Đăng ký thẻ mới.
```json
{
  "card_uid": "TAG-8F2B10",
  "owner_name": "Nguyen Van A",
  "vehicle_plate": "30A-99999",
  "card_type": "STANDARD"
}
```

#### `GET /api/v1/sessions/active`
Danh sách các xe đang đỗ trong bãi.

#### `GET /api/v1/sessions/history`
Lịch sử phiên gửi xe đã hoàn thành.

---

### 1.5. Simulator Control Endpoints

#### `POST /api/v1/simulator/slot-toggle`
Đảo trạng thái có xe / không có xe của một ô đỗ trên Simulator.
```json
{
  "slot_id": "P01",
  "occupied": true
}
```

#### `POST /api/v1/simulator/inject-mismatch`
Giả lập lỗi không khớp giữa Camera và Cảm biến để kiểm thử cảnh báo.
```json
{
  "slot_id": "P01",
  "sensor_occupied": true,
  "camera_occupied": false
}
```

#### `POST /api/v1/simulator/reset`
Đặt lại toàn bộ trạng thái bãi đỗ về mặc định (trống cả 4 ô).

---

## 2. WebSocket Protocol (`/ws/live`)

Frontend thiết lập kết nối WebSocket tới `/ws/live` để nhận luồng sự kiện theo thời gian thực.

Mọi gói tin phát ra đều có cấu trúc:
```json
{
  "event_type": "SLOT_UPDATE | GATE_ACTION | MISMATCH_ALERT | STATS_UPDATE",
  "timestamp": "2026-11-01T07:30:00Z",
  "data": { ... }
}
```

### Ví dụ các sự kiện:
1. **`SLOT_UPDATE`**:
```json
{
  "event_type": "SLOT_UPDATE",
  "timestamp": "2026-11-01T07:30:00Z",
  "data": {
    "slot_id": "P01",
    "status": "OCCUPIED",
    "sensor_distance_cm": 18.5,
    "available_slots": 3
  }
}
```

2. **`MISMATCH_ALERT`**:
```json
{
  "event_type": "MISMATCH_ALERT",
  "timestamp": "2026-11-01T07:30:00Z",
  "data": {
    "slot_id": "P02",
    "sensor_occupied": true,
    "camera_occupied": false,
    "severity": "WARNING",
    "message": "Mismatch detected on P02: Sensor reports OCCUPIED but Camera reports EMPTY."
  }
}
```
