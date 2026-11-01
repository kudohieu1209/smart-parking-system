# KIẾN TRÚC LUỒNG DỮ LIỆU THỜI GIAN THỰC — ESP32 ↔ BACKEND ↔ FRONTEND
## ESP32 FIRMWARE ↔ FASTAPI REST/WS ↔ REACT WEB DASHBOARD

**Dự án:** Smart Parking System — ESP32 + RFID + Camera AI + IoT  
**Mục tiêu tài liệu:** Đặc tả chi tiết kiến trúc luồng dữ liệu thời gian thực, mô hình phân tách quyết định xác thực và xác nhận cơ cấu chấp hành (Decoupled Actuator Telemetry), cùng cơ chế khóa liên động an toàn (Safety Interlock).

---

## 1. Sơ đồ Kiến trúc Tổng quan (System Topology)

```mermaid
flowchart TD
    subgraph EdgeLayer["1. Edge Hardware / Simulator (ESP32 & Sensors)"]
        HC["4x HC-SR04 (P01..P04)"]
        RFID["2x MFRC522 (Entry / Exit)"]
        SERVO["2x Servo Barrier (PWM 50Hz)"]
        IR["2x Safety Beam Sensors"]
        LCD["LCD 1602 I2C"]
        ESP["ESP32 Core (FreeRTOS)"]
        HC --> ESP
        RFID --> ESP
        IR --> ESP
        ESP --> SERVO
        ESP --> LCD
    end

    subgraph BackendLayer["2. Backend Server (FastAPI REST & WebSocket)"]
        API["FastAPI REST Endpoints (/api/v1)"]
        HAL["Hardware Abstraction Layer (HAL)"]
        DB[(SQLite / PostgreSQL DB)]
        WS["WebSocket Manager (/ws)"]
        API --> HAL
        API --> DB
        API --> WS
    end

    subgraph FrontendLayer["3. Client Presentation (React Dashboard)"]
        DASH["React 18 Dashboard (Vite SPA)"]
        UI_SLOT["Slot Visualizer (P01..P04)"]
        UI_GATE["Barrier & Gate Controls"]
        UI_STATS["Stats & Alerts Stream"]
        DASH --> UI_SLOT
        DASH --> UI_GATE
        DASH --> UI_STATS
    end

    ESP -- "HTTP POST (JSON Telemetry & Taps)" --> API
    WS -- "Realtime WebSocket Push (JSON Events)" --> DASH
    DASH -- "REST Control Commands" --> API
```

---

## 2. Luồng Dữ liệu Đo đạc Cảm biến Siêu âm (Ultrasonic Telemetry Flow)

ESP32 đọc khoảng cách định kỳ qua tác vụ `sensor_task` (Core 1), lưu snapshot vào Mutex, và `network_task` (Core 0) gửi dữ liệu lên Backend mỗi 2 giây.

```mermaid
sequenceDiagram
    autonumber
    actor Car as Phương tiện
    participant ESP as ESP32 (sensor_task)
    participant Backend as FastAPI (/telemetry/sensors)
    participant DB as SQLite Database
    participant WS as WebSocket Hub
    participant Dashboard as React Dashboard

    Car->>ESP: Xe tiến vào ô đỗ P01 (Khoảng cách < 25cm)
    ESP->>ESP: Lọc trung vị + Hysteresis -> Xác định P01=OCCUPIED
    ESP->>Backend: HTTP POST /api/v1/telemetry/sensors (readings=[P01..P04])
    Backend->>DB: Cập nhật sensor_occupied = true cho P01
    Backend->>WS: Broadcast SLOTS_BULK_UPDATE
    WS->>Dashboard: Push JSON payload cập nhật ô đỗ
    Dashboard->>Dashboard: Re-render Card P01 sang màu đỏ (OCCUPIED), Giảm chỗ trống còn 3
```

---

## 3. Luồng Quẹt thẻ & Phân tách Quyết định Xác thực (Decoupled RFID Flow)

Nguyên tắc an toàn: Backend chỉ đưa ra quyết định **cho phép/từ chối**. Trạng thái cánh barie trên Dashboard chỉ được hiển thị là **OPEN** khi ESP32 thực tế đã điều khiển servo và gửi telemetry phản hồi.

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Lái xe
    participant Reader as RFID Reader (RC522)
    participant ESP as ESP32 (rfid_task)
    participant Backend as FastAPI (/gate/entry-tap)
    participant Servo as Servo Cổng Vào
    participant WS as WebSocket Hub
    participant Dashboard as React Dashboard

    Driver->>Reader: Quẹt thẻ RFID (UID 30:A1:23:45)
    Reader->>ESP: Đọc UID qua SPI VSPI
    ESP->>Backend: HTTP POST /api/v1/gate/entry-tap {card_uid, gate_id: "ENTRY"}
    Note over Backend: Kiểm tra thẻ hợp lệ, bãi còn chỗ, không trùng phiên
    Backend-->>ESP: HTTP 200 {status: "ALLOWED", action: "OPEN_BARRIER"}
    Note over Dashboard: Trạng thái Barie trên Web VẪN LÀ "CLOSED" (Chưa nhận tín hiệu phần cứng)
    ESP->>Servo: barrier_open() -> Phát xung PWM 50Hz quay 90 độ
    ESP->>Backend: HTTP POST /api/v1/gate/barrier-state {gate_id: "ENTRY", state: "OPEN", angle: 90}
    Backend->>WS: Broadcast BARRIER_UPDATE {state: "OPEN", angle: 90}
    WS->>Dashboard: Cập nhật giao diện cánh barie mở 90 độ
```

---

## 4. Luồng Khóa Liên động An toàn (Safety Interlock Sequence)

Cảm biến quang an toàn (Safety Beam / Active LOW) ngăn chặn barie hạ đè vào xe. Khi phát hiện vật cản, bộ đếm đóng 3 giây bị hủy bỏ và giữ barie mở cho đến khi hoàn toàn thông thoáng liên tục trong 3000ms.

```mermaid
sequenceDiagram
    autonumber
    actor Car as Xe đi qua cổng
    participant IR as Cảm biến quang (IR Beam)
    participant ESP as ESP32 (barrier_task)
    participant Backend as FastAPI (/gate/safety-sensor)
    participant Servo as Servo Barrier
    participant Dashboard as React Dashboard

    Note over ESP: Barie đang mở (90 độ), đếm lùi thời gian hạ barie...
    Car->>IR: Xe dừng giữa barie -> Che khuất chùm tia hồng ngoại
    IR->>ESP: Chân GPIO 33 chuyển mức LOW (Vật cản phát hiện)
    ESP->>ESP: Xóa clear_counter_ms = 0 (Khóa liên động kích hoạt)
    ESP->>Backend: HTTP POST /api/v1/gate/safety-sensor {gate_id: "ENTRY", has_obstruction: true}
    Backend->>Dashboard: Broadcast SAFETY_SENSOR_UPDATE (obstruction: true)
    Dashboard->>Dashboard: Hiển thị cảnh báo vật cản đỏ tại Cổng Vào
    Note over Dashboard: Mọi lệnh "Hạ Barie" từ Dashboard lúc này bị Backend chặn từ chối (HTTP 400)
    Car->>IR: Xe đi hẳn vào bãi -> Chùm tia thông thoáng trở lại
    IR->>ESP: Chân GPIO 33 lên HIGH
    ESP->>Backend: HTTP POST /api/v1/gate/safety-sensor {gate_id: "ENTRY", has_obstruction: false}
    ESP->>ESP: Đếm lùi an toàn đủ 3000ms liên tục không có vật cản
    ESP->>Servo: barrier_close() -> Quay servo về góc 0 độ
    ESP->>Backend: HTTP POST /api/v1/gate/barrier-state {gate_id: "ENTRY", state: "CLOSED", angle: 0}
    Backend->>Dashboard: Broadcast BARRIER_UPDATE {state: "CLOSED", angle: 0}
    Dashboard->>Dashboard: Cập nhật cánh barie đóng phẳng (0 độ)
```
