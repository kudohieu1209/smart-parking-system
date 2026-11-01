# HƯỚNG DẪN VẬN HÀNH CHẾ ĐỘ MÔ PHỎNG (FULL SOFTWARE SIMULATION GUIDE)
## SMART PARKING SYSTEM — ESP32 + RFID + CAMERA AI + IOT DASHBOARD

Tài liệu này cung cấp hướng dẫn từng bước để thiết lập, chạy thử và kiểm chứng toàn bộ hệ thống Smart Parking System trên máy tính cá nhân chạy Windows (PowerShell) khi chưa có phần cứng vật lý.

---

## 1. Yêu Cầu Môi Trường (Prerequisites)

- **Hệ điều hành:** Windows 10/11 64-bit
- **Python:** 3.10 trở lên (khuyên dùng Python 3.11 - 3.14)
- **Node.js:** v18.0 trở lên (khuyên dùng v20+ hoặc v24)
- **PowerShell:** PowerShell 5.1 hoặc PowerShell 7+

---

## 2. Cài Đặt Môi Trường (One-time Setup)

Mở PowerShell tại thư mục gốc của dự án (`SMART-PARKING-SYSTEM`):

### 2.1. Cài đặt Backend Python Dependencies
```powershell
pip install -r backend/requirements.txt
```

### 2.2. Cài đặt Frontend Node Modules
```powershell
cd frontend
npm install
cd ..
```

---

## 3. Khởi Chạy Toàn Bộ Hệ Thống (Startup Guide)

Để trải nghiệm đầy đủ giao diện trực quan và các luồng sự kiện thời gian thực, khuyến nghị mở **3 cửa sổ PowerShell riêng biệt**:

### Cửa Sổ 1: Khởi động FastAPI Backend & WebSocket Hub
```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```
- **REST API Docs:** Mở trình duyệt tại [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### Cửa Sổ 2: Khởi động React Web Dashboard
```powershell
cd frontend
npm run dev
```
- **Web Dashboard:** Mở trình duyệt tại [http://localhost:5173](http://localhost:5173)

### Cửa Sổ 3: Khởi động Camera AI Synthetic Stream
```powershell
python vision/src/camera_stream.py
```
- Module này sẽ tự động sinh luồng video giả lập 4 ô đỗ xe và truyền phát trực tiếp qua giao thức MJPEG lên Dashboard tại `/api/v1/vision/live-feed`.

---

## 4. Sử Dụng Các Công Cụ Giả Lập Phần Cứng (Simulator CLI Tools)

Hệ thống cung cấp sẵn các CLI tool độc lập giúp tương tác nhanh với bãi đỗ xe:

### 4.1. Giả lập cảm biến siêu âm ESP32 (`mock_esp32.py`)
Gửi số liệu khoảng cách mượt mà và trạng thái chiếm dụng của 4 ô:
```powershell
# Chế độ luồng xe tự động ra vào ngẫu nhiên:
python simulator/mock_esp32.py --traffic --interval 2.0

# Hoặc đặt thủ công ô P01 có xe đỗ:
python simulator/mock_esp32.py --slot P01 --occupied
```

### 4.2. Giả lập quẹt thẻ RFID RC522 (`mock_rfid.py`)
Mô phỏng thao tác quẹt thẻ tại Cổng Vào hoặc Cổng Ra:
```powershell
# Quẹt thẻ hợp lệ vào cổng:
python simulator/mock_rfid.py --card RFID-DEMO-01 --gate ENTRY

# Quẹt thẻ ra cổng để thanh toán phí:
python simulator/mock_rfid.py --card RFID-DEMO-01 --gate EXIT

# Quẹt thẻ lạ (chưa đăng ký):
python simulator/mock_rfid.py --card UNKNOWN-CARD-99 --gate ENTRY

# Quẹt thẻ đã bị khóa:
python simulator/mock_rfid.py --card RFID-DEMO-02 --gate ENTRY
```

### 4.3. Giả lập Barrier Servo & Cảm Biến An Toàn (`mock_barrier.py`)
Kiểm thử khóa liên động bảo vệ cánh barie:
```powershell
# Mở barrier cổng vào:
python simulator/mock_barrier.py --gate ENTRY --command OPEN

# Giả lập vật cản (xe đỗ dưới cánh chắn):
python simulator/mock_barrier.py --gate ENTRY --obstruct

# Thử hạ barrier khi có vật cản -> Sẽ bị từ chối an toàn:
python simulator/mock_barrier.py --gate ENTRY --command CLOSE

# Giải tỏa vật cản và đóng an toàn:
python simulator/mock_barrier.py --gate ENTRY --clear
python simulator/mock_barrier.py --gate ENTRY --command CLOSE
```

---

## 5. Chạy Kiểm Thử Tự Động (Automated Testing)

### 5.1. Chạy Toàn Bộ 22 Unit & Integration Tests (Pytest)
```powershell
python -m pytest -v
```
Kết quả kiểm thử bao gồm:
- 9 Unit tests API nghiệp vụ
- 10 Automated Integration Tests (Edge cases, Anti-passback, Mismatch, Safety Interlock, Concurrency)
- 3 Vision tests (Synthetic Stream, ROI Extraction, Baseline Heuristic Detector)

### 5.2. Chạy 5 Kịch Bản Mô Phỏng Tuần Tự (E2E Scenario Suite)
Khi FastAPI backend đang chạy tại port 8000:
```powershell
python simulator/scenarios/run_all_scenarios.py
```
Bộ kịch bản sẽ tự động chạy:
1. `scenario_1_normal_flow`: Quy trình xe vào, đỗ, rời bãi, thanh toán cước tiêu chuẩn.
2. `scenario_2_parking_full`: Xử lý từ chối xe khi bãi đã đầy 4/4 vị trí.
3. `scenario_3_invalid_rfid`: Thẻ lạ, thẻ khóa, Anti-passback, thẻ chưa check-in.
4. `scenario_4_sensor_camera_mismatch`: Phát hiện sai lệch cảm biến vs camera và tự hòa giải.
5. `scenario_5_barrier_safety`: Khóa an toàn ngăn hạ cánh tay đòn khi có vật cản.

---

## 6. Chuyển Đổi Giữa Chế Độ SIMULATION Và HARDWARE

Hệ thống được thiết kế theo mô hình Hardware Abstraction Layer (HAL). Bạn có thể kiểm tra hoặc chuyển đổi chế độ hệ thống:

```powershell
# Xem chế độ hiện tại:
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/system/mode"

# Chuyển sang chế độ HARDWARE (khóa các endpoint giả lập):
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/system/mode?mode=HARDWARE"

# Chuyển lại về chế độ SIMULATION:
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/system/mode?mode=SIMULATION"
```
