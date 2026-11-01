# SMART PARKING SYSTEM — HỆ THỐNG BÃI ĐỖ XE THÔNG MINH

> **Đồ án Kỹ thuật Nhúng & IoT:** Tích hợp Vi điều khiển ESP32, RFID RC522, Cảm biến siêu âm HC-SR04, Thị giác máy tính OpenCV và Web Dashboard thời gian thực (FastAPI + React TypeScript).

![Simulation Mode](https://img.shields.io/badge/Mode-Simulation%20Active-amber)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20SQLAlchemy%20%7C%20WebSocket-0284c7)
![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript%20%7C%20Vite-6366f1)
![Firmware](https://img.shields.io/badge/Firmware-ESP--IDF%20C%20%7C%20FreeRTOS-e11d48)
![Vision](https://img.shields.io/badge/Vision-OpenCV%20Python-10b981)

---

## 1. Giới thiệu tổng quan

Hệ thống quản lý bãi đỗ xe thông minh quy mô mô hình gồm:
- **4 vị trí đỗ xe:** `P01`, `P02`, `P03`, `P04`.
- **1 Cổng vào (Entry Gate):** Tích hợp đầu đọc RFID và Barrier Servo tự động.
- **1 Cổng ra (Exit Gate):** Tích hợp đầu đọc RFID, tính cước tự động theo thời lượng đỗ và Barrier Servo.
- **Giám sát kép Cảm biến & Camera AI:** So sánh chéo liên tục giữa cảm biến siêu âm và camera nhận diện ROI để phát hiện sự cố không khớp (Mismatch Alert).
- **Hỗ trợ chế độ Simulation / Mock hoàn chỉnh:** Toàn bộ hệ thống có thể phát triển, chạy thử và kiểm thử tự động ngay trên máy tính mà chưa cần phần cứng vật lý.

---

## 2. Cấu trúc thư mục dự án

```text
SMART-PARKING-SYSTEM/
│
├── docs/                       # Tài liệu thiết kế kỹ thuật (Tiếng Việt)
│   ├── requirements.md         # Yêu cầu chức năng & phi chức năng chi tiết
│   ├── architecture.md         # Kiến trúc hệ thống phân tầng & sơ đồ Mermaid
│   ├── system-flow.md          # Quy trình vào, đỗ xe, ra bãi & lưu đồ tuần tự
│   ├── api-contract.md         # Đặc tả chi tiết REST API & WebSocket
│   ├── database-design.md      # Thiết kế cơ sở dữ liệu & quan hệ ERD
│   └── hardware-pinmap.md      # Sơ đồ chân GPIO tham chiếu dự kiến
│
├── firmware/                   # Mã nguồn nhúng ESP32 (ESP-IDF C + FreeRTOS)
│   └── esp32/
│       ├── CMakeLists.txt
│       ├── main/
│       │   ├── main.c          # 4 FreeRTOS tasks: sensor, rfid, barrier, network
│       │   └── CMakeLists.txt
│       ├── components/
│       │   ├── parking_core/   # Định nghĩa kiểu & pin_config.h
│       │   ├── sensor/         # Driver cảm biến siêu âm HC-SR04
│       │   ├── rfid/           # Driver đầu đọc RC522 qua SPI
│       │   ├── barrier/        # Điều khiển Servo PWM & cảm biến an toàn
│       │   ├── network/        # Client truyền thông HTTP/MQTT
│       │   └── display/        # Hiển thị LCD 1602 I2C
│       └── README.md           # Hướng dẫn cài đặt ESP-IDF và nạp firmware
│
├── backend/                    # Core Backend API & Business Logic
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, Lifespan & WebSocket
│   │   ├── api/v1/router.py    # REST API endpoints cho slots, gate, telemetry
│   │   ├── core/config.py      # Cấu hình hệ thống & biến môi trường
│   │   ├── database/session.py # SQLAlchemy session & SQLite connection
│   │   ├── models/parking.py   # ORM models (Slot, Card, Session, Alert)
│   │   ├── schemas/parking.py  # Pydantic v2 validation schemas
│   │   └── services/           # Nghiệp vụ: tính phí, so sánh sai lệch, WS hub
│   ├── tests/test_api.py       # Unit tests kiểm tra API & luồng nghiệp vụ
│   └── requirements.txt
│
├── frontend/                   # Web Dashboard giao diện người dùng
│   ├── src/
│   │   ├── components/         # Slot cards, Barrier, RFID panel, Controls, Tables
│   │   ├── services/api.ts     # Giao tiếp HTTP REST & WebSocket
│   │   ├── types/index.ts      # TypeScript interfaces
│   │   ├── App.tsx             # Main Dashboard logic & WebSocket listener
│   │   ├── main.tsx
│   │   └── index.css           # Modern dark UI theme
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── vision/                     # Module Thị giác máy tính nhận diện 4 ô đỗ
│   ├── config/roi_config.json  # Toạ độ 4 vùng ROI (P01..P04)
│   ├── samples/                # Video MP4 mẫu & frame mẫu mô phỏng bãi xe
│   │   ├── sample_parking.mp4  # Video MP4 120 frames xe ra vào
│   │   ├── frame_empty.jpg
│   │   ├── frame_p01_occupied.jpg
│   │   └── frame_all_occupied.jpg
│   ├── src/
│   │   ├── camera_stream.py    # SyntheticStream, OpenCVDeviceStream, OpenCVFileStream, MJPEG Generator
│   │   ├── roi_manager.py      # Cắt patch ROI & vẽ lớp phủ trực quan
│   │   ├── occupancy_detector.py # Interface & Heuristic Baseline detector
│   │   └── main.py             # Runner đẩy telemetry nhận diện về Backend
│   └── tests/test_vision.py    # Kiểm thử module thị giác
│
├── simulator/                  # Bộ công cụ giả lập phần cứng (Full Software Simulation)
│   ├── mock_esp32.py           # Giả lập ESP32, khoảng cách siêu âm & Auto Traffic
│   ├── mock_rfid.py            # Giả lập quẹt thẻ vào/ra, khóa thẻ, Anti-passback
│   ├── mock_barrier.py         # Giả lập Servo Barrier (0-90°) & Cảm biến an toàn IR
│   ├── mock_camera.py          # Giả lập kết quả nhận diện camera
│   └── scenarios/              # 5 Kịch bản kiểm thử tự động chuyên sâu
│       ├── scenario_1_normal_flow.py            # Quy trình vào/ra tiêu chuẩn
│       ├── scenario_2_parking_full.py           # Từ chối khi bãi đã đầy 4/4 ô
│       ├── scenario_3_invalid_rfid.py           # Thẻ lạ, thẻ khóa, Anti-passback
│       ├── scenario_4_sensor_camera_mismatch.py # Xung đột cảm biến vs camera
│       ├── scenario_5_barrier_safety.py         # Khóa liên động cảm biến an toàn
│       └── run_all_scenarios.py                 # Bộ chạy tự động cả 5 kịch bản
│
├── scripts/                    # Scripts tiện ích chạy trên Windows PowerShell
│   ├── run_backend.ps1
│   ├── run_frontend.ps1
│   ├── run_simulator.ps1
│   ├── run_vision.ps1
│   ├── run_e2e_test.ps1        # Chạy toàn bộ 5 kịch bản mô phỏng
│   └── generate_sample_video.py # Sinh video MP4 & ảnh mẫu
│
├── .env.example                # Mẫu biến môi trường
├── .gitignore
└── README.md
```

---

## 3. Hướng dẫn cài đặt & Khởi động trên Windows PowerShell

### 3.1. Cài đặt Dependencies

**1. Cài đặt Python Packages (Backend, Vision, Simulator):**
```powershell
pip install -r backend/requirements.txt
```

**2. Cài đặt Node.js Packages (Frontend):**
```powershell
cd frontend
npm install
cd ..
```

---

### 3.2. Khởi động các dịch vụ

Mở các cửa sổ PowerShell riêng biệt cho từng thành phần:

#### Cửa sổ 1: Khởi động Backend API Server (Port 8000)
```powershell
.\scripts\run_backend.ps1
# Hoặc: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Truy cập tài liệu tương tác Swagger: 👉 `http://localhost:8000/docs`

#### Cửa sổ 2: Khởi động Web Dashboard (Port 5173)
```powershell
.\scripts\run_frontend.ps1
# Hoặc: cd frontend; npm run dev
```
- Mở trình duyệt tại: 👉 `http://localhost:5173`

---

## 4. Chạy kiểm thử tự động (Automated Verification)

Hệ thống được tích hợp bộ test tự động đầy đủ:

### 1. Kiểm thử Backend API & Nghiệp vụ (Pytest)
```powershell
python -m pytest backend/tests/test_api.py -v
```
*Kiểm tra: Root endpoint, Healthcheck, Khởi tạo 4 ô đỗ, Check-in vào cổng, Quy tắc Anti-passback, Check-out tính cước, Simulator toggle, Inject Mismatch.*

### 2. Kiểm thử Module Thị giác máy tính (Pytest Vision)
```powershell
python -m pytest vision/tests/test_vision.py -v
```
*Kiểm tra: Luồng giả lập Synthetic Stream 640x480, Cắt 4 ROI patches, Thuật toán cơ sở phân loại EMPTY vs OCCUPIED, Vẽ lớp phủ trực quan.*

### 3. Chạy toàn bộ 5 kịch bản kiểm thử mô phỏng nâng cao (Full Simulation Suite)
Sau khi Backend đang chạy tại `http://localhost:8000`:
```powershell
.\scripts\run_e2e_test.ps1
# Hoặc: python simulator/scenarios/run_all_scenarios.py
```
*Tự động thực thi tuần tự và nghiệm thu 5 kịch bản:*
1. **Kịch bản 1:** Quy trình tiêu chuẩn xe vào/ra bãi (`scenario_1_normal_flow.py`)
2. **Kịch bản 2:** Xử lý từ chối xe khi bãi đỗ đã đầy 4/4 ô (`scenario_2_parking_full.py`)
3. **Kịch bản 3:** Kiểm soát thẻ RFID không hợp lệ, thẻ khóa & Anti-passback (`scenario_3_invalid_rfid.py`)
4. **Kịch bản 4:** Động cơ phát hiện và giải tỏa xung đột Cảm biến vs Camera (`scenario_4_sensor_camera_mismatch.py`)
5. **Kịch bản 5:** Khóa liên động an toàn Barrier khi có vật cản dưới cánh chắn (`scenario_5_barrier_safety.py`)

---

## 5. Thử nghiệm Chế độ Mô phỏng trên Web Dashboard

Bạn có thể tương tác trực tiếp trên giao diện Web Dashboard (`http://localhost:5173`):

1. **Xem trực tiếp luồng Camera AI Simulator:** Theo dõi luồng video trực tiếp với lớp phủ 4 vùng ROI (P01..P04), bật/tắt stream hoặc chụp ảnh snapshot từ video MP4 mẫu `vision/samples/sample_parking.mp4`.
2. **Kiểm soát Barrier Servo & Cảm biến an toàn:**
   - Quan sát góc mở thanh chắn (0° - 90°) và thanh đo góc servo.
   - Thử bấm nút **"Mô phỏng vật cản dưới barrier"** để kích hoạt cảm biến quang IR.
   - Thử bấm **"Hạ Barrier (0°)"** khi có vật cản: Hệ thống sẽ từ chối hạ cánh và kích hoạt cảnh báo an toàn màu đỏ.
3. **Mô phỏng RFID & Quản lý thẻ:**
   - Quét thẻ vào/ra bãi.
   - Bấm **"Khóa Thẻ Này"** để chuyển thẻ sang `LOCKED` và thử quét vào cổng để kiểm tra từ chối `CARD_INACTIVE`.
   - Bấm **"Quét Thẻ Lạ"** để kiểm tra phản hồi từ chối `CARD_UNKNOWN`.
4. **Thay đổi trạng thái ô đỗ & Sai lệch:**
   - Bấm **"Đỗ xe vào"** / **"Rời ô đỗ"** trên từng ô P01..P04.
   - Bấm **"Lỗi Mismatch"** để kiểm tra cảnh báo xung đột vàng cam nhấp nháy.
   - Bấm **"Lấp đầy 4 ô"**, **"Làm trống 4 ô"** hoặc **"Đặt lại hệ thống"**.


---

## 6. Kế hoạch phát triển tiếp theo (Next Steps)

Sau khi hoàn thành và nghiệm thu **Giai đoạn 1 — Project Initialization**:
- **Giai đoạn 2 (Firmware & Hardware Integration):** Kết nối phần cứng ESP32 thật, đọc xung Echo từ HC-SR04, giao tiếp SPI với RC522 và điều khiển Servo qua PWM.
- **Giai đoạn 3 (Camera AI Upgrade):** Thu thập dữ liệu video bãi đỗ thực tế, huấn luyện mô hình YOLOv8-nano nhận diện phương tiện và tích hợp vào module `vision`.
- **Giai đoạn 4 (Advanced Business Logic):** Tích hợp cổng thanh toán trực tuyến QR Code (VietQR / MoMo), hệ thống đặt chỗ trước (Reservation), và xác thực JWT cho quản trị viên.
