"""
KỊCH BẢN 3: KIỂM THỬ CÁC TRƯỜNG HỢP THẺ RFID KHÔNG HỢP LỆ & ANTI-PASSBACK
Kiểm thử 4 trường hợp ngoại lệ về thẻ:
1. Thẻ chưa từng đăng ký trong hệ thống (CARD_UNKNOWN).
2. Thẻ đã bị khóa / ngưng kích hoạt (CARD_INACTIVE).
3. Quét thẻ lặp nhiều lần tại cổng vào / Anti-passback (CARD_ALREADY_IN_USE).
4. Quét thẻ tại cổng ra khi chưa từng check-in vào bãi (NO_ACTIVE_SESSION).
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
    print(" [KỊCH BẢN 3] BẮT ĐẦU KIỂM THỬ THẺ RFID KHÔNG HỢP LỆ & ANTI-PASSBACK")
    print("="*75)

    # 1. Reset
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    # TRƯỜNG HỢP 1: Thẻ chưa từng đăng ký
    print("[1] Kiểm thử Thẻ lạ / chưa đăng ký (RFID-UNKNOWN-99)...")
    resp_unknown = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-UNKNOWN-99",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert resp_unknown["status"] == "REJECTED"
    assert resp_unknown["reason"] == "CARD_UNKNOWN"
    assert resp_unknown["action"] == "KEEP_CLOSED"
    print(f" -> OK: Từ chối đúng chuẩn! [{resp_unknown['reason']}] - {resp_unknown['message']}")

    # TRƯỜNG HỢP 2: Thẻ bị khoá
    print("[2] Kiểm thử Thẻ đã bị khóa trong hệ thống (RFID-DEMO-02)...")
    # Khóa thẻ 02
    requests.post(f"{base_url}/cards/toggle-active", json={"card_uid": "RFID-DEMO-02", "is_active": False}, timeout=5)
    resp_inactive = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-02",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert resp_inactive["status"] == "REJECTED"
    assert resp_inactive["reason"] == "CARD_INACTIVE"
    print(f" -> OK: Từ chối đúng chuẩn! [{resp_inactive['reason']}] - {resp_inactive['message']}")
    # Mở khóa lại thẻ
    requests.post(f"{base_url}/cards/toggle-active", json={"card_uid": "RFID-DEMO-02", "is_active": True}, timeout=5)

    # TRƯỜNG HỢP 3: Quẹt lặp tại cổng vào (Anti-passback)
    print("[3] Kiểm thử Quét lặp 2 lần tại cổng vào (Anti-passback với RFID-DEMO-03)...")
    # Lần 1: Thành công
    first_tap = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-03",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert first_tap["status"] == "ALLOWED"
    print(f" -> Lần 1: Check-in thành công (Phiên #{first_tap['session']['id']})")

    # Lần 2: Quét tiếp ngay lập tức khi chưa check-out -> Bị chặn
    second_tap = requests.post(f"{base_url}/gate/entry-tap", json={
        "card_uid": "RFID-DEMO-03",
        "gate_id": "ENTRY"
    }, timeout=5).json()
    assert second_tap["status"] == "REJECTED"
    assert second_tap["reason"] == "CARD_ALREADY_IN_USE"
    print(f" -> OK: Lần 2 bị chặn Anti-passback chuẩn xác! [{second_tap['reason']}] - {second_tap['message']}")

    # TRƯỜNG HỢP 4: Quét thẻ tại cổng ra khi chưa từng vào bãi
    print("[4] Kiểm thử Quét thẻ ra khi thẻ chưa có phiên vào (RFID-DEMO-04)...")
    resp_no_session = requests.post(f"{base_url}/gate/exit-tap", json={
        "card_uid": "RFID-DEMO-04",
        "gate_id": "EXIT"
    }, timeout=5).json()
    assert resp_no_session["status"] == "REJECTED"
    assert resp_no_session["reason"] == "NO_ACTIVE_SESSION"
    print(f" -> OK: Từ chối đúng chuẩn! [{resp_no_session['reason']}] - {resp_no_session['message']}")

    # Dọn dẹp phiên thử nghiệm
    requests.post(f"{base_url}/gate/exit-tap", json={"card_uid": "RFID-DEMO-03", "gate_id": "EXIT"}, timeout=5)
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    print("\n" + "="*75)
    print(" >>> KỊCH BẢN 3: THÀNH CÔNG 100% <<< ")
    print("="*75)
    return True

if __name__ == "__main__":
    run_test()
