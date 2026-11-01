"""
MOCK BARRIER CONTROLLER — Giả lập động cơ Servo Barrier & Cảm biến quang an toàn.
Giao tiếp với Backend qua REST API để kiểm soát góc mở (0° - 90°) và chùm tia an toàn.
"""

import sys
import time
import argparse
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1"

class MockBarrier:
    def __init__(self, base_url: str = DEFAULT_BACKEND_URL):
        self.base_url = base_url

    def set_safety_obstruction(self, gate_id: str, has_obstruction: bool) -> dict:
        """Kích hoạt hoặc giải tỏa cảm biến an toàn (vật cản chặn cánh barie)."""
        url = f"{self.base_url}/gate/safety-sensor"
        payload = {"gate_id": gate_id.upper(), "has_obstruction": has_obstruction}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            status = "CÓ VẬT CẢN" if has_obstruction else "ĐÃ THÔNG THOÁNG"
            print(f"[BARRIER SAFETY] Gate {gate_id.upper()}: Cảm biến quang -> {status}")
            return resp.json()
        except Exception as e:
            print(f"[BARRIER ERROR] Không thể gửi tín hiệu an toàn: {e}")
            return {"status": "ERROR", "message": str(e)}

    def command(self, gate_id: str, action: str) -> dict:
        """Gửi lệnh OPEN hoặc CLOSE đến barrier."""
        url = f"{self.base_url}/gate/command"
        payload = {"gate_id": gate_id.upper(), "command": action.upper()}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            if resp.status_code == 200:
                print(f"[BARRIER CMD SUCCESS] Gate {gate_id.upper()} -> {action.upper()}: {data.get('message')}")
            else:
                print(f"[BARRIER CMD REJECTED] Gate {gate_id.upper()} -> {action.upper()}: {data.get('detail')}")
            return data
        except Exception as e:
            print(f"[BARRIER ERROR] Không thể gửi lệnh điều khiển: {e}")
            return {"status": "ERROR", "message": str(e)}

    def simulate_vehicle_passage(self, gate_id: str, transit_seconds: float = 2.0):
        """Mô phỏng chu trình xe đi qua cổng an toàn:
        1. Mở barrier (90°)
        2. Xe tiến vào -> Cảm biến an toàn phát hiện vật cản (Obstruction = True)
        3. Thử lệnh đóng barrier -> Bị từ chối vì không an toàn
        4. Xe đi qua hoàn toàn -> Cảm biến an toàn thông thoáng (Obstruction = False)
        5. Đóng barrier an toàn (0°)
        """
        g = gate_id.upper()
        print(f"\n--- Bắt đầu mô phỏng xe lưu thông qua cổng {g} ---")

        # 1. Mở barrier
        self.command(g, "OPEN")
        time.sleep(0.5)

        # 2. Xe dừng giữa cổng
        print(f"[SIM] Xe đang di chuyển qua cổng {g} (chắn cảm biến an toàn)...")
        self.set_safety_obstruction(g, True)
        time.sleep(1.0)

        # 3. Thử đóng trong khi xe còn kẹt
        print(f"[SIM] Thử hạ barrier trong khi xe đang ở dưới cánh chắn:")
        self.command(g, "CLOSE")
        time.sleep(transit_seconds)

        # 4. Xe đã ra khỏi vùng quét
        print(f"[SIM] Xe đã đi qua cổng hoàn toàn, giải phóng vùng chắn an toàn...")
        self.set_safety_obstruction(g, False)
        time.sleep(0.5)

        # 5. Đóng barrier an toàn
        self.command(g, "CLOSE")
        print(f"--- Hoàn tất chu trình xe qua cổng {g} an toàn ---\n")

def main():
    parser = argparse.ArgumentParser(description="Mock Barrier & Safety Sensor Simulator")
    parser.add_argument("--gate", choices=["ENTRY", "EXIT"], default="ENTRY", help="Gate identifier")
    parser.add_argument("--action", choices=["open", "close", "obstruct", "clear", "passage"], required=True,
                        help="Action to perform")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Backend API URL")

    args = parser.parse_args()
    barrier = MockBarrier(base_url=args.url)

    if args.action == "open":
        barrier.command(args.gate, "OPEN")
    elif args.action == "close":
        barrier.command(args.gate, "CLOSE")
    elif args.action == "obstruct":
        barrier.set_safety_obstruction(args.gate, True)
    elif args.action == "clear":
        barrier.set_safety_obstruction(args.gate, False)
    elif args.action == "passage":
        barrier.simulate_vehicle_passage(args.gate)

if __name__ == "__main__":
    main()
