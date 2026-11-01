"""
KỊCH BẢN 1: QUY TRÌNH TIÊU CHUẨN XE VÀO/RA BÃI (NORMAL VEHICLE FLOW)
Kiểm thử chu trình đầy đủ:
1. Reset hệ thống về trạng thái sạch.
2. Xe đến cổng vào -> Quẹt thẻ RFID hợp lệ (RFID-DEMO-01).
3. Barrier cổng vào mở (90°).
4. Xe qua cổng an toàn -> Barrier cổng vào đóng lại (0°).
5. Xe tiến vào ô đỗ P01 -> Cảm biến siêu âm & Camera xác nhận OCCUPIED.
6. Xe nổ máy rời ô đỗ P01 -> Ô đỗ quay lại trạng thái EMPTY.
7. Xe đến cổng ra -> Quẹt thẻ RFID-DEMO-01.
8. Hệ thống tính cước tự động, hoàn tất phiên đỗ, mở barrier cổng ra.
9. Xe đi qua an toàn -> Barrier cổng ra đóng lại.
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

def run_test(base_url: str = BASE_URL):
    print("\n" + "="*75)
    print(" [KỊCH BẢN 1] BẮT ĐẦU KIỂM THỬ QUY TRÌNH XE VÀO/RA TIÊU CHUẨN")
    print("="*75)

    # 1. Reset
    print("[1] Đặt lại hệ thống về trạng thái ban đầu...")
    resp = requests.post(f"{base_url}/simulator/reset", timeout=5)
    assert resp.status_code == 200, "Reset phải thành công"

    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    assert slots["available_slots"] == 4, "Cả 4 ô phải trống lúc đầu"
    print(f" -> OK: Tổng số ô={slots['total_slots']}, Chỗ trống={slots['available_slots']}")

    # 2. Quét thẻ cổng vào
    print("[2] Xe biển số 30A-123.45 quẹt thẻ RFID-DEMO-01 tại Cổng Vào...")
    tap_resp = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-01",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert tap_resp["status"] == "ALLOWED", "Thẻ hợp lệ phải được cho phép vào"
    assert tap_resp["action"] == "OPEN_BARRIER", "Barrier phải được lệnh mở"
    session_id = tap_resp["session"]["id"]
    print(f" -> OK: Cổng vào mở. Phiên gửi xe khởi tạo #{session_id} [{tap_resp['message']}]")

    # 3. Xe đi qua cổng an toàn
    print("[3] Mô phỏng xe di chuyển qua cổng vào an toàn...")
    # Cảm biến an toàn phát hiện xe
    requests.post(f"{base_url}/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": True}, timeout=5)
    # Xe đi qua hết, cảm biến clear
    requests.post(f"{base_url}/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": False}, timeout=5)
    # Đóng barrier
    close_resp = requests.post(f"{base_url}/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"}, timeout=5)
    assert close_resp.status_code == 200
    print(" -> OK: Xe đã qua cổng, Barrier cổng vào đã đóng an toàn (0°).")

    # 4. Xe đỗ vào ô P01
    print("[4] Xe tiến vào vị trí đỗ P01 (Cảm biến siêu âm & Camera cùng phát hiện)...")
    requests.post(f"{base_url}/telemetry/sensors", json={
        "device_id": "ESP32_01",
        "readings": [{"slot_id": "P01", "distance_cm": 18.2, "occupied": True}]
    }, timeout=5)
    requests.post(f"{base_url}/vision/occupancy", json={
        "camera_id": "CAM_01",
        "slots": [{"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.96}]
    }, timeout=5)

    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    p01 = next(s for s in slots["slots"] if s["slot_id"] == "P01")
    assert p01["status"] == "OCCUPIED"
    assert p01["has_mismatch"] is False
    print(f" -> OK: Ô P01 chuyển sang trạng thái OCCUPIED (Còn trống: {slots['available_slots']}/4)")

    # 5. Xe rời ô đỗ
    print("[5] Xe rời khỏi ô P01...")
    requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": "P01", "occupied": False}, timeout=5)
    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    p01 = next(s for s in slots["slots"] if s["slot_id"] == "P01")
    assert p01["status"] == "EMPTY"
    print(" -> OK: Ô P01 trở về trạng thái EMPTY.")

    # 6. Quẹt thẻ cổng ra
    print("[6] Xe đến cổng ra và quẹt thẻ RFID-DEMO-01...")
    exit_resp = requests.post(f"{base_url}/gate/exit-tap", json={
        "card_uid": "RFID-DEMO-01",
        "gate_id": "EXIT"
    }, timeout=5).json()
    assert exit_resp["status"] == "ALLOWED", "Thẻ hợp lệ phải được cho phép xuất bãi"
    assert exit_resp["action"] == "OPEN_BARRIER", "Barrier cổng ra phải mở"
    sess = exit_resp["session"]
    assert sess["status"] == "COMPLETED"
    print(f" -> OK: Cổng ra mở. Phiên xe #{sess['id']} hoàn tất. Cước phí: {sess['fee_amount']:,} VNĐ ({sess['duration_minutes']} phút)")

    # 7. Xe qua cổng ra và đóng barrier
    requests.post(f"{base_url}/gate/command", json={"gate_id": "EXIT", "command": "CLOSE"}, timeout=5)
    print(" -> OK: Xe đã rời khỏi bãi, Barrier cổng ra đã đóng an toàn.")

    print("\n" + "="*75)
    print(" >>> KỊCH BẢN 1: THÀNH CÔNG 100% <<< ")
    print("="*75)
    return True

if __name__ == "__main__":
    run_test()
