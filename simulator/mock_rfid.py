"""
MOCK RFID READER — Giả lập đầu đọc thẻ RFID RC522 tại Cổng Vào / Cổng Ra.
Hỗ trợ quẹt thẻ hợp lệ, thẻ lạ (chưa đăng ký), thẻ bị khoá và kiểm thử Anti-passback.
"""

import sys
import argparse
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1"

class MockRFID:
    def __init__(self, base_url: str = DEFAULT_BACKEND_URL):
        self.base_url = base_url

    def tap_entry(self, card_uid: str) -> dict:
        url = f"{self.base_url}/gate/entry-tap"
        payload = {"card_uid": card_uid, "gate_id": "ENTRY"}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            status_text = "HỢP LỆ (MỞ CỔNG)" if data.get('status') == 'ALLOWED' else f"TỪ CHỐI [{data.get('reason')}]"
            print(f"[RFID ENTRY TAP] Thẻ: {card_uid} -> {status_text} | Msg: {data.get('message')}")
            return data
        except Exception as e:
            print(f"[RFID ERROR] Không thể kết nối Backend: {e}")
            return {"status": "ERROR", "message": str(e)}

    def tap_exit(self, card_uid: str) -> dict:
        url = f"{self.base_url}/gate/exit-tap"
        payload = {"card_uid": card_uid, "gate_id": "EXIT"}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            status_text = "HỢP LỆ (XUẤT BÃI)" if data.get('status') == 'ALLOWED' else f"TỪ CHỐI [{data.get('reason')}]"
            print(f"[RFID EXIT TAP] Thẻ: {card_uid} -> {status_text} | Msg: {data.get('message')}")
            if data.get("session"):
                s = data["session"]
                print(f"                Cước: {s.get('fee_amount'):,} VNĐ | Thời lượng: {s.get('duration_minutes')} phút")
            return data
        except Exception as e:
            print(f"[RFID ERROR] Không thể kết nối Backend: {e}")
            return {"status": "ERROR", "message": str(e)}

    def toggle_card_status(self, card_uid: str, is_active: bool) -> dict:
        """Khóa hoặc mở khóa thẻ RFID."""
        url = f"{self.base_url}/cards/toggle-active"
        payload = {"card_uid": card_uid, "is_active": is_active}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            action_name = "KÍCH HOẠT" if is_active else "KHÓA THẺ"
            print(f"[RFID ADMIN] Đã {action_name} thẻ: {card_uid}")
            return resp.json()
        except Exception as e:
            print(f"[RFID ERROR] Không thể cập nhật trạng thái thẻ: {e}")
            return {"status": "ERROR", "message": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Mock RFID Card Tap Simulator")
    parser.add_argument("--action", choices=["entry", "exit", "lock", "unlock"], required=True, help="Action to perform")
    parser.add_argument("--card", default="RFID-DEMO-01", help="Card UID (e.g. RFID-DEMO-01 or RFID-UNKNOWN-99)")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Backend API URL")

    args = parser.parse_args()
    rfid = MockRFID(base_url=args.url)

    if args.action == "entry":
        rfid.tap_entry(args.card)
    elif args.action == "exit":
        rfid.tap_exit(args.card)
    elif args.action == "lock":
        rfid.toggle_card_status(args.card, False)
    elif args.action == "unlock":
        rfid.toggle_card_status(args.card, True)

if __name__ == "__main__":
    main()
