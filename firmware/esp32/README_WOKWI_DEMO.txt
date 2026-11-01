================================================================================
  CẢNH BÁO QUAN TRỌNG: FIRMWARE MÔ PHỎNG WOKWI DEMO ONLY
================================================================================

TẬP TIN BINARY NÀY LÀ BẢN BUILD ĐẶC BIỆT CHỈ DÀNH CHO TRÌNH MÔ PHỎNG WOKWI.
TUYỆT ĐỐI KHÔNG ĐƯỢC NẠP LÊN PHẦN CỨNG VI ĐIỀU KHIỂN ESP32 THẬT!

Mục đích thiết kế:
- Cho phép kiểm thử hoạt động của 2 Servo Barrier (LEDC PWM 50Hz) và 2 Công tắc
  cảm biến quang an toàn (GPIO 33 / GPIO 16) trên trình giả lập Wokwi ngay cả khi
  không có kết nối Backend hoặc không phân giải được host.wokwi.internal.
- Trong chế độ này, chỉ 2 thẻ demo nằm trong whitelist:
  + Cổng Vào (Entry Gate): UID 30:A1:23:45
  + Cổng Ra  (Exit Gate):  UID 01:02:03:04
  mới được phép mở cổng khi Backend ngoại tuyến.
- Mọi thẻ RFID lạ khác ngoài danh sách này ĐỀU BỊ TỪ CHỐI TUYỆT ĐỐI.

Khi triển khai trên phần cứng thật:
- BẮT BUỘC sử dụng firmware từ artifact chính thức: 'esp32-firmware-binaries'
- Chế độ phần cứng thật (Hardware Mode) tuân thủ nghiêm ngặt nguyên tắc Fail-Safe:
  Toàn bộ lệnh mở barrier bắt buộc phải có chứng thực hợp lệ từ FastAPI Backend.
================================================================================
