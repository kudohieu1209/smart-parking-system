# BÁO CÁO KẾT QUẢ KIỂM THỬ TÍCH HỢP — PHASE 3.5
## WOKWI ESP32 ↔ FASTAPI BACKEND ↔ REACT DASHBOARD REALTIME INTEGRATION

**Dự án:** Smart Parking System — ESP32 + RFID + Camera AI + IoT  
**Môi trường thử nghiệm:**
- **OS:** Windows 11 Pro 64-bit
- **Python:** Python 3.14.5 / 3.12 (CI)
- **Node.js / Vite:** Node.js v20.x, Vite v6.4.5, React 18, TypeScript 5.2
- **ESP-IDF:** v5.3 (Espressif Docker Container qua GitHub Actions)
- **Git Commit:** `aab4098` (`feat: integrate wokwi esp32 with fastapi realtime backend`)
- **GitHub Actions CI Run:** [#41314975182](https://github.com/kudohieu1209/smart-parking-system/actions/runs/41314975182) (SUCCESS)
  - `esp32-firmware-binaries` (5.3 MB)
  - `esp32-wokwi-demo-only` (4.7 MB)

---

## 1. Tổng kết Trạng thái Xác minh Toàn hệ thống

| Hạng mục kiểm thử | Công cụ / Môi trường | Số test case | Kết quả | Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API & Nghiệp vụ** | Pytest 9.0.3 + HTTPX TestClient | 24 / 24 | **100% PASS** | Bao gồm test luồng quẹt thẻ, telemetry 4 ô đỗ, tính phí, xử lý bất đồng bộ, race condition. |
| **Phân tách Quyết định & Phản hồi Thực tế (Decoupling)** | Pytest (`test_phase3_5_hardware_mode_telemetry_and_decoupling`) | 1 / 1 | **100% PASS** | Đảm bảo trong Hardware Mode, Backend cho phép nhưng trạng thái barie không tự đổi sang OPEN cho đến khi nhận POST `/gate/barrier-state`. |
| **Khóa Liên động An toàn (Safety Interlock)** | Pytest & Firmware Logic | 2 / 2 | **100% PASS** | Từ chối lệnh đóng khi có vật cản; tự động reset bộ đếm 3s an toàn khi chùm tia bị chặn. |
| **Giao diện Web Frontend** | TypeScript Compiler + Vite Production Build | Toàn bộ components | **PASS** | Đóng gói thành công bundle production không có lỗi cảnh báo TypeScript (`tsc && vite build`). |
| **Biên dịch Firmware ESP-IDF** | GitHub Actions ESP-IDF v5.3 | 2 Build Profiles | **PASS** (CI Workflow) | Biên dịch cả bản Production (Fail-Safe) và Standalone Wokwi Demo. |
| **Wokwi Simulator Runtime Trực tiếp** | Trình duyệt / Wokwi Extension | 15 Kịch bản tương tác | **NOT VERIFIED** | **Chưa kiểm chứng thời gian thực trực tiếp trên Wokwi máy host** do thiếu Wokwi Private Gateway kết nối ra bên ngoài trên môi trường tự động hóa không có GUI tương tác. Người dùng cần chạy theo Hướng dẫn Tích hợp để quan sát thực tế. |

---

## 2. Chi tiết Kết quả Kiểm thử Phần mềm Tự động (24 Pytest Suites)

```text
backend/tests/test_api.py::test_root_endpoint PASSED                     [  4%]
backend/tests/test_api.py::test_health_endpoint PASSED                   [  8%]
backend/tests/test_api.py::test_get_slots PASSED                         [ 12%]
backend/tests/test_api.py::test_entry_and_exit_tap_flow PASSED           [ 16%]
backend/tests/test_api.py::test_simulator_slot_toggle PASSED             [ 20%]
backend/tests/test_api.py::test_simulator_inject_mismatch PASSED         [ 25%]
backend/tests/test_api.py::test_barrier_safety_and_commands PASSED       [ 29%]
backend/tests/test_api.py::test_card_toggle_active PASSED                [ 33%]
backend/tests/test_api.py::test_system_mode_toggle PASSED                [ 37%]
backend/tests/test_api.py::test_phase3_5_hardware_mode_telemetry_and_decoupling PASSED [ 41%]
backend/tests/test_integration_10_scenarios.py::test_01_normal_entry_flow PASSED [ 45%]
backend/tests/test_integration_10_scenarios.py::test_02_invalid_rfid PASSED [ 50%]
backend/tests/test_integration_10_scenarios.py::test_03_parking_full PASSED [ 54%]
backend/tests/test_integration_10_scenarios.py::test_04_anti_passback PASSED [ 58%]
backend/tests/test_integration_10_scenarios.py::test_05_exit_and_fee_calculation PASSED [ 62%]
backend/tests/test_integration_10_scenarios.py::test_06_sensor_camera_mismatch PASSED [ 66%]
backend/tests/test_integration_10_scenarios.py::test_07_barrier_safety_interlock PASSED [ 70%]
backend/tests/test_integration_10_scenarios.py::test_08_esp32_telemetry_timeout PASSED [ 75%]
backend/tests/test_integration_10_scenarios.py::test_09_camera_signal_loss PASSED [ 79%]
backend/tests/test_integration_10_scenarios.py::test_10_high_concurrency_race_condition PASSED [ 83%]
backend/tests/test_integration_10_scenarios.py::test_11_wokwi_standardized_hex_rfid_cards PASSED [ 87%]
vision/tests/test_vision.py::test_synthetic_camera_stream PASSED         [ 91%]
vision/tests/test_vision.py::test_roi_manager_extraction PASSED          [ 95%]
vision/tests/test_vision.py::test_baseline_detector_empty_and_occupied PASSED [100%]
```

---

## 3. Lý do Kỹ thuật Đánh dấu Wokwi Runtime là `NOT VERIFIED`

1. **Giới hạn Môi trường Gateway Cloud Sandbox của Wokwi Web:**
   - Phiên bản miễn phí của Wokwi Web chạy code mô phỏng trong một Docker sandbox trên đám mây của Wokwi.
   - Khi firmware gọi `http_client` tới `http://host.wokwi.internal:8000/api/v1`, tên miền này không được phân giải trong sandbox công cộng (lỗi `getaddrinfo() returns 202`).
   - Để kết nối được, người dùng cần chạy qua một trong 3 giải pháp mạng (Xem tài liệu [Hướng dẫn Tích hợp Wokwi ↔ Backend](file:///D:/Vibe/Project/SMART-PARKING-SYSTEM/docs/hardware/wokwi-backend-integration-guide.md)).

2. **Chính sách Thẩm định Nghiêm ngặt (Strict Verification Policy):**
   - Đảm bảo tính trung thực tuyệt đối của tài liệu kỹ thuật: Không tự tiện đánh dấu `PASS` khi chưa có bản ghi Serial Monitor xác nhận kết nối TCP socket thành công từ Wokwi tới máy host.
   - Khi người dùng khởi chạy Wokwi theo các bước hướng dẫn và kết nối thành công, trạng thái này sẽ được cập nhật từ `NOT VERIFIED` thành `VERIFIED & PASSED`.
