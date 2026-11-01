"""
KỊCH BẢN 2: KIỂM THỬ XỬ LÝ KHI BÃI ĐỖ XE ĐÃ ĐẦY (PARKING FULL REJECTION)
Kiểm thử quy tắc nghiệp vụ:
1. Chiếm dụng toàn bộ 4 vị trí đỗ P01..P04 (available_slots = 0).
2. Xe thứ 5 tiến vào cổng và quẹt thẻ RFID.
3. Hệ thống kiểm tra bãi đầy -> TỪ CHỐI (REJECTED), Barrier không mở.
4. Hệ thống ghi nhận cảnh báo PARKING_FULL vào cơ sở dữ liệu.
5. Một xe trong bãi rời ô đỗ (available_slots = 1).
6. Xe ngoài cổng quẹt lại -> Được chấp nhận (ALLOWED) và mở barrier.
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
    print(" [KỊCH BẢN 2] BẮT ĐẦU KIỂM THỬ XỬ LÝ KHI BÃI ĐỖ XE ĐÃ ĐẦY")
    print("="*75)

    # 1. Reset
    print("[1] Đặt lại hệ thống...")
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    # 2. Chiếm dụng cả 4 ô đỗ
    print("[2] Lấp đầy cả 4 vị trí đỗ (P01, P02, P03, P04)...")
    for s_id in ["P01", "P02", "P03", "P04"]:
        requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": s_id, "occupied": True}, timeout=5)

    slots = requests.get(f"{base_url}/slots", timeout=5).json()
    assert slots["available_slots"] == 0, "Bãi đỗ phải có 0 chỗ trống"
    print(f" -> OK: Trạng thái bãi xe: Tổng={slots['total_slots']}, Đang đỗ={slots['occupied_slots']}, Còn trống={slots['available_slots']}")

    # 3. Xe thứ 5 quẹt thẻ vào bãi
    print("[3] Xe mang thẻ RFID-DEMO-01 quẹt thẻ vào khi bãi đã đầy 4/4 ô...")
    tap_resp = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-01",
        "gate_id": "ENTRY"
    }, timeout=5).json()

    assert tap_resp["status"] == "REJECTED", "Bãi đầy bắt buộc phải từ chối check-in"
    assert tap_resp["action"] == "KEEP_CLOSED", "Barrier phải giữ đóng"
    assert tap_resp["reason"] == "PARKING_FULL", "Lý do từ chối phải là PARKING_FULL"
    print(f" -> OK: Từ chối chuẩn xác! Trạng thái={tap_resp['status']} | Lý do={tap_resp['reason']} | Msg={tap_resp['message']}")

    # 4. Kiểm tra cảnh báo PARKING_FULL trong cơ sở dữ liệu
    print("[4] Kiểm tra danh sách cảnh báo hệ thống...")
    alerts = requests.get(f"{base_url}/system/alerts", timeout=5).json()
    full_alerts = [a for a in alerts if a["alert_type"] == "PARKING_FULL"]
    assert len(full_alerts) > 0, "Hệ thống phải tự động tạo cảnh báo PARKING_FULL"
    print(f" -> OK: Phát hiện cảnh báo #{full_alerts[0]['id']} [{full_alerts[0]['message']}]")

    # 5. Giải phóng 1 ô đỗ (P02)
    print("[5] Một xe trong bãi rời khỏi ô P02...")
    requests.post(f"{base_url}/simulator/slot-toggle", json={"slot_id": "P02", "occupied": False}, timeout=5)
    slots_after = requests.get(f"{base_url}/slots", timeout=5).json()
    assert slots_after["available_slots"] == 1, "Bãi phải có 1 chỗ trống"
    print(f" -> OK: Vị trí P02 đã trống (Số chỗ còn lại: {slots_after['available_slots']}/4)")

    # 6. Xe quẹt thẻ lại sau khi có chỗ trống
    print("[6] Xe quẹt lại thẻ RFID-DEMO-01 tại cổng vào...")
    retry_resp = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-01",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert retry_resp["status"] == "ALLOWED", "Đã có chỗ trống thì phải cho phép vào"
    assert retry_resp["action"] == "OPEN_BARRIER", "Barrier phải mở"
    print(f" -> OK: Check-in thành công sau khi có chỗ trống! [{retry_resp['message']}]")

    # Dọn dẹp
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    print("\n" + "="*75)
    print(" >>> KỊCH BẢN 2: THÀNH CÔNG 100% <<< ")
    print("="*75)
    return True

if __name__ == "__main__":
    run_test()
