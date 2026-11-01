"""
KỊCH BẢN 4: KIỂM THỬ XUNG ĐỘT TRẠNG THÁI CẢM BIẾN SIÊU ÂM VS CAMERA AI (MISMATCH ENGINE)
Kiểm thử tính năng cốt lõi:
1. Trường hợp 1: Cảm biến siêu âm báo CÓ XE (18cm), nhưng Camera AI báo TRỐNG.
   -> Trạng thái ô chuyển sang MISMATCH, hệ thống phát cảnh báo SENSOR_CAMERA_MISMATCH.
2. Trường hợp 2: Camera AI báo CÓ XE (96%), nhưng Cảm biến siêu âm báo TRỐNG (120cm).
   -> Trạng thái ô chuyển sang MISMATCH, hệ thống phát cảnh báo.
3. Giải toả xung đột: Khi cả hai nguồn dữ liệu thống nhất trạng thái, cờ MISMATCH tự động được gỡ bỏ.
"""

import sys
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api/v1"

def run_test(base_url: str = BASE_URL):
    print("\n" + "="*75)
    print(" [KỊCH BẢN 4] BẮT ĐẦU KIỂM THỬ XUNG ĐỘT CẢM BIẾN VS CAMERA AI")
    print("="*75)

    # 1. Reset
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    # TRƯỜNG HỢP 1: Cảm biến có xe, Camera báo trống tại P01
    print("[1] Giả lập Ô P01: Cảm biến siêu âm = CÓ XE, Camera AI = TRỐNG...")
    requests.post(f"{base_url}/simulator/inject-mismatch", json={
        "slot_id": "P01",
        "sensor_occupied": True,
        "camera_occupied": False
    }, timeout=5)

    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    p01 = next(s for s in slots["slots"] if s["slot_id"] == "P01")
    assert p01["status"] == "MISMATCH", "Ô P01 phải có trạng thái MISMATCH"
    assert p01["has_mismatch"] is True, "Cờ has_mismatch phải bật True"
    print(f" -> OK: Ô P01 chuyển sang MISMATCH chuẩn xác! (Sensor={p01['sensor_occupied']}, Camera={p01['camera_occupied']})")

    # Kiểm tra cảnh báo trong danh sách alerts
    alerts = requests.get(f"{base_url}/system/alerts", timeout=5).json()
    p01_alerts = [a for a in alerts if a["alert_type"] == "SENSOR_CAMERA_MISMATCH" and a["slot_id"] == "P01"]
    assert len(p01_alerts) > 0, "Phải ghi nhận cảnh báo SENSOR_CAMERA_MISMATCH cho P01"
    print(f" -> OK: Hệ thống đã tạo cảnh báo #{p01_alerts[0]['id']} [{p01_alerts[0]['message']}]")

    # TRƯỜNG HỢP 2: Camera có xe, Cảm biến báo trống tại P03
    print("\n[2] Giả lập Ô P03: Camera AI = CÓ XE, Cảm biến siêu âm = TRỐNG...")
    requests.post(f"{base_url}/simulator/inject-mismatch", json={
        "slot_id": "P03",
        "sensor_occupied": False,
        "camera_occupied": True
    }, timeout=5)

    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    p03 = next(s for s in slots["slots"] if s["slot_id"] == "P03")
    assert p03["status"] == "MISMATCH"
    assert p03["has_mismatch"] is True
    print(f" -> OK: Ô P03 chuyển sang MISMATCH chuẩn xác! (Sensor={p03['sensor_occupied']}, Camera={p03['camera_occupied']})")

    # TRƯỜNG HỢP 3: Giải toả xung đột
    print("\n[3] Đồng bộ hoá dữ liệu để giải toả xung đột:")
    print(" -> Ô P01: Cả hai xác nhận CÓ XE (OCCUPIED)...")
    requests.post(f"{base_url}/telemetry/sensors", json={
        "device_id": "ESP32_01",
        "readings": [{"slot_id": "P01", "distance_cm": 18.0, "occupied": True}]
    }, timeout=5)
    requests.post(f"{base_url}/vision/occupancy", json={
        "camera_id": "CAM_01",
        "slots": [{"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.98}]
    }, timeout=5)

    print(" -> Ô P03: Cả hai xác nhận TRỐNG (EMPTY)...")
    requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": "P03", "occupied": False}, timeout=5)

    slots_after = requests.get(f"{base_url}/slots", timeout=5).json()
    p01_resolved = next(s for s in slots_after["slots"] if s["slot_id"] == "P01")
    p03_resolved = next(s for s in slots_after["slots"] if s["slot_id"] == "P03")

    assert p01_resolved["status"] == "OCCUPIED" and p01_resolved["has_mismatch"] is False
    assert p03_resolved["status"] == "EMPTY" and p03_resolved["has_mismatch"] is False
    print(" -> OK: Cả hai ô P01 và P03 đã giải tỏa cảnh báo MISMATCH và trở lại trạng thái đồng bộ hoàn hảo!")

    # Dọn dẹp
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    print("\n" + "="*75)
    print(" >>> KỊCH BẢN 4: THÀNH CÔNG 100% <<< ")
    print("="*75)
    return True

if __name__ == "__main__":
    run_test()
