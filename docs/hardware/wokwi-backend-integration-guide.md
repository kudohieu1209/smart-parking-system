# HƯỚNG DẪN KẾT NỐI TÍCH HỢP WOKWI ESP32 VỚI FASTAPI BACKEND
## WOKWI SIMULATOR ↔ FASTAPI (PORT 8000) ↔ REACT DASHBOARD (PORT 5173)

**Dự án:** Smart Parking System — ESP32 + RFID + Camera AI + IoT  
**Mục tiêu:** Cấu hình và vận hành kết nối thời gian thực giữa vi điều khiển ESP32 giả lập trên Wokwi và máy chủ FastAPI Backend chạy trên máy tính cá nhân (Host OS).

---

## 1. Phân tích Bản chất Vấn đề Kết nối Mạng Wokwi

Khi ESP32 chạy trên trình duyệt Wokwi Web (bản miễn phí):
- Máy ảo ESP32 chạy trong một sandbox cloud độc lập. Mạng Wi-Fi ảo `Wokwi-GUEST` không thể truy cập trực tiếp các địa chỉ private IP (`192.168.x.x` hay `127.0.0.1`) của máy host do cách ly firewall.
- `host.wokwi.internal` là hostname đặc biệt do Wokwi thiết kế, nhưng **chỉ hoạt động** khi:
  1. Chạy qua **Wokwi Extension trong VS Code / Antigravity IDE** (chạy trực tiếp trên máy host).
  2. Chạy qua **Wokwi IoT Gateway** (Local Gateway client).
  3. Hoặc chuyển hướng qua **Public Tunnel** (Cloudflare Tunnel / Ngrok).

Dưới đây là 3 phương án kết nối thực tế:

---

## 2. Phương án A (KHUYẾN NGHỊ): Sử dụng Wokwi Extension trong VS Code / Antigravity

Đây là phương pháp chuẩn mực, ổn định nhất, không phụ thuộc vào Internet bandwidth và không bị hạn chế timeout.

### Bước 1: Cài đặt Extension Wokwi
1. Trong VS Code hoặc Antigravity IDE, vào tab **Extensions** (`Ctrl + Shift + X`).
2. Tìm kiếm **Wokwi Simulator** và chọn **Install**.
3. Nhấn `F1` (hoặc `Ctrl + Shift + P`), gõ:
   ```text
   Wokwi: Request a Free Trial License
   ```
   (Làm theo hướng dẫn xác thực để nhận license miễn phí).

### Bước 2: Khởi động Backend & Frontend trên Host
Mở PowerShell tại thư mục gốc dự án:
```powershell
# Terminal 1: Khởi động FastAPI Backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Khởi động React Web Dashboard
npm --prefix frontend run dev
```

### Bước 3: Khởi chạy Wokwi Simulator
1. Mở file `firmware/esp32/diagram.json`.
2. Nhấn nút **Play (Start Simulation)** màu xanh trên giao diện editor Wokwi.
3. Khi firmware boot, ESP32 sẽ kết nối vào `Wokwi-GUEST`, và các yêu cầu gửi tới `http://host.wokwi.internal:8000/api/v1` sẽ tự động được Wokwi Extension chuyển tiếp về `http://127.0.0.1:8000/api/v1`.

---

## 3. Phương án B: Sử dụng Wokwi IoT Gateway (Dành cho Wokwi Web)

Nếu bạn muốn chạy mô phỏng trên nền tảng web `https://wokwi.com`:

### Bước 1: Tải Wokwi IoT Gateway
Wokwi cung cấp tiện ích gateway chuyển tiếp mạng cho Wokwi Web:
- Tải file nhị phân Wokwi Gateway cho Windows: [Wokwi IoT Gateway Releases](https://github.com/wokwi/wokwi-features/issues/212)
- Hoặc chạy qua lệnh PowerShell:
  ```powershell
  # Chạy Wokwi Gateway trên máy host
  wokwigw.exe
  ```

### Bước 2: Bật Wi-Fi Gateway trong dự án Wokwi Web
Trong file `diagram.json` trên Wokwi Web, đảm bảo cấu hình kết nối Wi-Fi sử dụng gateway local.

---

## 4. Phương án C: Sử dụng Reverse Tunnel (Cloudflare Tunnel / Ngrok)

Phương án này cực kỳ tiện lợi nếu muốn dùng Wokwi Web trực tiếp mà không cần cài thêm gateway client.

### Bước 1: Mở tunnel tới cổng 8000 bằng Cloudflared
Mở PowerShell và chạy lệnh:
```powershell
# Chạy Cloudflare Tunnel miễn phí (không cần tài khoản)
cloudflared tunnel --url http://localhost:8000
```
Terminal sẽ trả về một đường link công khai dạng:
`https://random-subdomain.trycloudflare.com`

### Bước 2: Thiết lập Base URL cho ESP32
Trong Kconfig hoặc cấu hình firmware, bạn có thể truyền Base URL này:
- URL API: `https://random-subdomain.trycloudflare.com/api/v1`

---

## 5. Quy trình Kiểm thử Thực tế 1 Xe Vào và Ra (Single Turnaround Test)

1. **Chuẩn bị cấu hình thẻ đồng nhất:**
   - Trong `firmware/esp32/diagram.json`, cấu hình cả 2 đầu đọc `rfid_entry` và `rfid_exit` cùng UID `30:A1:23:45`:
   ```json
   {
     "type": "board-mfrc522",
     "id": "rfid_entry",
     "top": 240,
     "left": -260,
     "attrs": { "uid": "30:A1:23:45" }
   },
   {
     "type": "board-mfrc522",
     "id": "rfid_exit",
     "top": 240,
     "left": -60,
     "attrs": { "uid": "30:A1:23:45" }
   }
   ```

2. **Chạy kịch bản xe vào (Check-in):**
   - Click vào thẻ xanh của `rfid_entry` trên Wokwi.
   - Quan sát Serial: `>>> ENTRY TAP: Card UID = 30:A1:23:45 <<<`
   - Backend xác thực: `status: ALLOWED`, `action: OPEN_BARRIER`.
   - Servo `servo_entry` quay lên góc 90 độ.
   - ESP32 gửi `POST /api/v1/gate/barrier-state` (`ENTRY`, `OPEN`, `90`).
   - Web Dashboard (`http://localhost:5173`) hiển thị cánh barie Cổng Vào mở.

3. **Mô phỏng xe đỗ vào ô P01:**
   - Click vào cảm biến `ultrasonic1` (P01) trên Wokwi, kéo thanh trượt khoảng cách xuống 15 cm.
   - Sau 2 giây, ESP32 gửi telemetry. Dashboard chuyển ô P01 sang màu đỏ (Đã có xe).
   - Màn hình LCD 1602 hiển thị `P:3 EMPTY`.

4. **Kiểm tra cảm biến an toàn (Safety Interlock):**
   - Trước khi barie đóng (trong 3s đầu), gạt switch `switch_safety_entry` (GPIO 33) sang ON (nối GND = Active LOW).
   - ESP32 phát hiện vật cản: `Gate ENTRY: Obstruction detected! SAFETY INTERLOCK ACTIVE: Barrier kept OPEN.`
   - Barie giữ nguyên mở, không hạ xuống.
   - Gạt switch về OFF: Hết vật cản, ESP32 đếm lùi 3 giây thông thoáng rồi đóng barie (`servo_entry` về 0 độ).
   - ESP32 gửi `POST /api/v1/gate/barrier-state` (`ENTRY`, `CLOSED`, `0`). Dashboard hạ barie.

5. **Chạy kịch bản xe ra (Check-out):**
   - Click vào thẻ của `rfid_exit` trên Wokwi.
   - Backend tìm thấy phiên `ACTIVE` của thẻ `30:A1:23:45`, tính phí gửi và đổi trạng thái `COMPLETED`.
   - Servo `servo_exit` quay lên 90 độ.
   - Dashboard hiển thị thông báo thanh toán và mở barie Cổng Ra.
   - Kéo cảm biến `ultrasonic1` lên 120 cm (xe rời ô đỗ).
   - Dashboard cập nhật ô P01 thành màu xanh (Trống, 4 chỗ khả dụng).
