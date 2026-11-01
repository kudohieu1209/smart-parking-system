"""
KỊCH BẢN KIỂM THỬ TOÀN TRÌNH (END-TO-END FULL CYCLE SCENARIO)
Kiểm tra tự động toàn bộ luồng:
1. Đặt lại trạng thái bãi đỗ (Reset).
2. Quét thẻ vào cổng (Entry Tap) -> Mở Barrier -> Khởi tạo phiên xe.
3. Xe vào đỗ tại ô P01 -> Cảm biến & Camera xác nhận OCCUPIED.
4. Giả lập cảnh báo sai lệch (Mismatch) tại P02.
5. Giải toả cảnh báo tại P02.
6. Xe rời ô đỗ P01 -> Trở về EMPTY.
7. Quét thẻ ra cổng (Exit Tap) -> Tính cước -> Hoàn tất phiên xe -> Mở Barrier.
"""

import sys
import time
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api/v1"

def log_step(step_num: int, title: str):
    print(f"\n{'='*70}\n[BƯỚC {step_num}] {title}\n{'='*70}")

def run_scenario(base_url: str = BASE_URL):
    print("Bắt đầu kịch bản kiểm thử toàn trình Smart Parking System...")

    # BƯỚC 1: Đặt lại trạng thái
    log_step(1, "Đặt lại trạng thái hệ thống (Reset)")
    resp = requests.post(f"{base_url}/simulator/reset", timeout=5)
    assert resp.status_code == 200
    print(" -> Hệ thống đã reset về trạng thái ban đầu.")

    slots_resp = requests.get(f"{base_url}/slots", timeout=5).json()
    print(f" -> Tổng số ô: {slots_resp['total_slots']}, Chỗ trống: {slots_resp['available_slots']}")
    assert slots_resp["available_slots"] == 4, "Tất cả 4 ô phải trống"

    # BƯỚC 2: Quét thẻ vào (Check-in)
    log_step(2, "Quét thẻ RFID vào cổng (Entry Check-in)")
    card_uid = "RFID-DEMO-01"
    entry_resp = requests.post(f"{base_url}/gate/entry-tap", json={"card_uid": card_uid, "gate_id": "ENTRY"}, timeout=5).json()
    print(f" -> Phản hồi vào cổng: Status={entry_resp['status']}, Action={entry_resp['action']}, Msg={entry_resp['message']}")
    assert entry_resp["status"] == "ALLOWED", "Thẻ hợp lệ phải được cho phép vào"
    assert entry_resp["action"] == "OPEN_BARRIER", "Barrier phải mở"
    session_id = entry_resp["session"]["id"]
    print(f" -> Phiên gửi xe khởi tạo thành công: ID = {session_id}")

    # Đóng barrier sau khi xe qua
    requests.post(f"{base_url}/gate/barrier-state", json={"gate_id": "ENTRY", "state": "CLOSED"}, timeout=5)
    print(" -> Xe đã qua cổng, Barrier cổng vào đóng lại.")

    # BƯỚC 3: Xe vào đỗ tại P01 (Cảm biến + Camera AI)
    log_step(3, "Xe di chuyển vào đỗ tại ô P01")
    # ESP32 gửi khoảng cách 18.2 cm (occupied = True)
    requests.post(f"{base_url}/telemetry/sensors", json={
        "device_id": "ESP32_DEV_01",
        "readings": [{"slot_id": "P01", "distance_cm": 18.2, "occupied": True}]
    }, timeout=5)
    # Camera AI xác nhận có xe tại ROI P01
    requests.post(f"{base_url}/vision/occupancy", json={
        "camera_id": "CAM_MAIN_01",
        "slots": [{"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.95}]
    }, timeout=5)

    slots_resp = requests.get(f"{base_url}/slots", timeout=5).json()
    p01 = next(s for s in slots_resp["slots"] if s["slot_id"] == "P01")
    print(f" -> Trạng thái ô P01: Status={p01['status']}, Sensor={p01['sensor_occupied']}, Cam={p01['camera_occupied']}")
    assert p01["status"] == "OCCUPIED"

    # BƯỚC 4: Giả lập lỗi sai lệch (Mismatch) tại P02
    log_step(4, "Kích hoạt kiểm thử sai lệch dữ liệu Cảm biến vs Camera tại P02")
    requests.post(f"{base_url}/simulator/inject-mismatch", json={
        "slot_id": "P02",
        "sensor_occupied": True,
        "camera_occupied": False
    }, timeout=5)

    slots_resp = requests.get(f"{base_url}/slots", timeout=5).json()
    p02 = next(s for s in slots_resp["slots"] if s["slot_id"] == "P02")
    print(f" -> Trạng thái ô P02: Status={p02['status']}, HasMismatch={p02['has_mismatch']}")
    assert p02["status"] == "MISMATCH"
    assert p02["has_mismatch"] is True
    print(" -> Hệ thống đã phát hiện và gán cờ MISMATCH thành công!")

    # BƯỚC 5: Giải toả lỗi tại P02
    log_step(5, "Giải toả sai lệch tại P02 (Xe không đỗ, camera và cảm biến đồng bộ EMPTY)")
    requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": "P02", "occupied": False}, timeout=5)
    slots_resp = requests.get(f"{base_url}/slots", timeout=5).json()
    p02 = next(s for s in slots_resp["slots"] if s["slot_id"] == "P02")
    assert p02["status"] == "EMPTY"
    print(f" -> Trạng thái ô P02 đã giải toả: {p02['status']}")

    # BƯỚC 6: Xe rời ô đỗ P01
    log_step(6, "Xe nổ máy rời khỏi ô đỗ P01")
    requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": "P01", "occupied": False}, timeout=5)
    slots_resp = requests.get(f"{base_url}/slots", timeout=5).json()
    p01 = next(s for s in slots_resp["slots"] if s["slot_id"] == "P01")
    assert p01["status"] == "EMPTY"
    print(f" -> Ô P01 đã trống trở lại: {p01['status']}")

    # BƯỚC 7: Quét thẻ ra cổng (Check-out & Billing)
    log_step(7, "Quét thẻ RFID tại cổng ra (Exit Check-out & Tính phí)")
    exit_resp = requests.post(f"{base_url}/gate/exit-tap", json={"card_uid": card_uid, "gate_id": "EXIT"}, timeout=5).json()
    print(f" -> Phản hồi ra cổng: Status={exit_resp['status']}, Action={exit_resp['action']}, Msg={exit_resp['message']}")
    assert exit_resp["status"] == "ALLOWED", "Thẻ hợp lệ phải được xuất bãi"
    assert exit_resp["action"] == "OPEN_BARRIER", "Barrier cổng ra phải mở"
    sess = exit_resp["session"]
    print(f" -> Phiên gửi xe hoàn tất: Thời gian={sess['duration_minutes']} phút, Cước phí={sess['fee_amount']:,} VNĐ")

    # Đóng barrier cổng ra
    requests.post(f"{base_url}/gate/barrier-state", json={"gate_id": "EXIT", "state": "CLOSED"}, timeout=5)

    # Thống kê cuối
    log_step(8, "Kiểm tra số liệu thống kê Dashboard")
    stats = requests.get(f"{base_url}/system/stats", timeout=5).json()
    print(f" -> Tổng số ô: {stats['total_slots']}")
    print(f" -> Ô đang trống: {stats['available_slots']}")
    print(f" -> Phiên đang hoạt động: {stats['active_sessions_count']}")
    print(f" -> Tổng doanh thu: {stats['total_revenue_vnd']:,} VNĐ")

    print("\n" + "="*70)
    print(" KỊCH BẢN KIỂM THỬ TOÀN TRÌNH ĐÃ HOÀN THÀNH XUẤT SẮC 100%! ")
    print("="*70)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    run_scenario(url)
