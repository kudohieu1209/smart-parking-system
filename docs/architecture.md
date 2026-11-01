# KIẾN TRÚC HỆ THỐNG — SMART PARKING SYSTEM

## 1. Tổng quan kiến trúc hệ thống

Hệ thống được thiết kế theo mô hình phân tầng hướng dịch vụ (Layered Event-Driven Architecture) gồm 4 phân hệ chính:
1. **Perception & Actuation Layer (Lớp thu thập & Điều khiển nhúng):** ESP32 Firmware / Python Mock Hardware.
2. **Vision Intelligence Layer (Lớp thị giác máy tính):** OpenCV Camera AI Module.
3. **Core Backend & Persistence Layer (Lớp dịch vụ trung tâm & Dữ liệu):** FastAPI, SQLAlchemy, SQLite, WebSocket Broadcaster.
4. **Presentation Layer (Lớp giao diện người dùng):** React Vite TypeScript Dashboard.

```mermaid
flowchart TD
    subgraph Physical_Or_Mock_Edge ["Edge Devices / Simulator"]
        direction TB
        ESP["ESP32 DevKit / Mock ESP32"]
        SENSORS["4x Ultrasonic HC-SR04 (P01-P04)"]
        RFID_IN["Entry RFID RC522"]
        RFID_OUT["Exit RFID RC522"]
        BARRIER_IN["Entry Servo Barrier"]
        BARRIER_OUT["Exit Servo Barrier"]
        CAM["Camera / Synthetic Video Stream"]

        SENSORS -->|Distance Data| ESP
        RFID_IN -->|Card UID Tap| ESP
        RFID_OUT -->|Card UID Tap| ESP
        ESP -->|PWM Signal| BARRIER_IN
        ESP -->|PWM Signal| BARRIER_OUT
    end

    subgraph Vision_Module ["Vision Intelligence Layer"]
        CAM -->|RTSP / USB / Mock Stream| CV_CORE["OpenCV Frame Processor"]
        CV_CORE -->|4 ROI Slot Analysis| CV_RESULTS["Occupancy Vector (P01..P04)"]
    end

    subgraph Backend_Core ["FastAPI Backend Core"]
        direction TB
        API_ROUTER["REST API Endpoints"]
        WS_MANAGER["WebSocket Realtime Hub"]
        SESSION_SRV["Parking Session Manager"]
        BILLING_SRV["Billing & Pricing Engine"]
        FUSION_SRV["Sensor-Vision Discrepancy Engine"]
        DB[(SQLite Database)]

        SESSION_SRV --> DB
        BILLING_SRV --> DB
        FUSION_SRV --> WS_MANAGER
    end

    subgraph Presentation ["Frontend Dashboard"]
        DASHBOARD["React + TS Web Dashboard"]
        SLOT_GRID["Interactive 4-Slot Canvas/Grid"]
        RFID_PANEL["Card Manager & Quick Tap Mock"]
        LOGS["Live Event & Mismatch Alerts"]
    end

    ESP <==>|HTTP POST / WebSocket JSON| API_ROUTER
    CV_RESULTS ==>|HTTP POST /api/v1/vision/occupancy| API_ROUTER
    API_ROUTER --> SESSION_SRV
    API_ROUTER --> FUSION_SRV
    WS_MANAGER <==>|WebSocket Stream (ws://)| DASHBOARD
    DASHBOARD ==>|REST API Calls| API_ROUTER
```

---

## 2. Chi tiết các tầng kiến trúc

### 2.1. Lớp Edge (Firmware ESP32 / Mock ESP32)
- **ESP32 Firmware (ESP-IDF C + FreeRTOS):**
  - **Task Sensor:** Định kỳ 500ms kích hoạt 4 cảm biến siêu âm HC-SR04 đo khoảng cách (cm). Áp dụng bộ lọc trung vị (Median Filter) để loại bỏ nhiễu rung động.
  - **Task RFID:** Lắng nghe ngắt SPI từ 2 đầu đọc MFRC522 (Entry/Exit). Khi phát hiện thẻ, gửi sự kiện `CARD_TAP` lên Backend.
  - **Task Barrier Control:** Nhận lệnh mở barrier từ Backend, điều khiển PWM góc 90°, kiểm tra cảm biến an toàn, tự động hạ sau khi xe qua.
  - **Task Network/Telemetry:** Gửi gói tin JSON định kỳ (1 giây) chứa trạng thái cảm biến và nhận chỉ thị điều khiển.
- **Simulator Mode (Python Mock):**
  - Giả lập hoàn hảo giao thức của ESP32 qua HTTP/REST hoặc WebSocket nội bộ. Cho phép kỹ sư kiểm thử toàn bộ luồng nghiệp vụ không cần phần cứng.

### 2.2. Lớp Vision Intelligence (OpenCV Python)
- Module đọc video từ webcam thật, file video mp4, hoặc bộ sinh ảnh mô phỏng đồ hoạ (Synthetic Video Generator).
- Cấu hình 4 vùng quan tâm (ROI - Region of Interest) định dạng toạ độ `(x, y, w, h)`.
- Trích xuất đặc trưng pixel (Background Subtraction / Edge Density / Texture) để phân loại `OCCUPIED` hoặc `EMPTY`.
- Đóng gói dữ liệu dạng mảng:
  `[{"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.92}, ...]` và đẩy về Backend qua REST API định kỳ hoặc khi có thay đổi.

### 2.3. Lớp Backend Core (FastAPI)
- **FastAPI Framework:** Hiệu năng cao, sinh tài liệu tương tác Swagger tự động tại `/docs`.
- **Dịch vụ Hợp nhất Cảm biến - Thị giác (Sensor-Vision Fusion):**
  - So sánh trạng thái từng ô đỗ được báo từ siêu âm với trạng thái nhận diện từ camera.
  - Nếu khác nhau vượt quá cửa sổ trễ (Debounce Time = 5 giây) -> Đánh dấu trạng thái ô là `MISMATCH` và đẩy cảnh báo đến Frontend qua WebSocket.
- **Quản lý Phiên (Session Manager):**
  - Quản lý vòng đời xe: `CREATED` -> `ACTIVE` (đã vào bãi) -> `COMPLETED` (đã thanh toán và ra khỏi bãi).
  - Phòng chống Double-tap và chống gian lận thẻ.
- **WebSocket Manager:** Duy trì kết nối hai chiều với Frontend Dashboard để cập nhật dữ liệu với độ trễ mili-giây.

### 2.4. Lớp Frontend (React + TypeScript + Vite)
- **Visual Parking Lot:** Hiển thị trực quan 4 ô đỗ dạng xe 2D với hiệu ứng màu sắc chuẩn UI công nghiệp:
  - 🟢 **Xanh lá:** `EMPTY` (Còn trống)
  - 🔴 **Đỏ:** `OCCUPIED` (Có xe đỗ)
  - 🟡 **Vàng cam:** `MISMATCH` (Bất thường cảm biến / camera)
  - ⚪ **Xám:** `DISCONNECTED` / `ERROR`
- **Simulation Control Bar:** Cung cấp các nút bấm giả lập trực tiếp trên giao diện:
  - Nút "Quẹt thẻ vào", "Quẹt thẻ ra".
  - Nút "Đặt xe vào ô P01/P02/P03/P04", "Rời ô đỗ".
  - Nút "Tạo lỗi không khớp Camera/Cảm biến".
- **Dashboard số liệu:** Thống kê xe đang gửi, doanh thu tích luỹ, danh sách phiên xe và nhật ký cảnh báo hệ thống.
