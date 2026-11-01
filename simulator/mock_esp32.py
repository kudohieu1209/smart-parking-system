"""
MOCK ESP32 — Giả lập bo mạch vi điều khiển ESP32 và cảm biến siêu âm 4 ô đỗ (P01..P04).
Cung cấp chế độ gửi telemetry định kỳ, chuyển tiếp khoảng cách mượt mà và sinh lưu lượng tự động (Auto Traffic).
"""

import sys
import time
import argparse
import random
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1"

class MockESP32:
    def __init__(self, base_url: str = DEFAULT_BACKEND_URL, device_id: str = "ESP32_MOCK_DEV"):
        self.base_url = base_url
        self.device_id = device_id
        # Trạng thái ban đầu: Cả 4 ô đều trống (khoảng cách ~ 120 cm)
        self.slots = {
            "P01": {"occupied": False, "distance": 120.0},
            "P02": {"occupied": False, "distance": 122.5},
            "P03": {"occupied": False, "distance": 118.0},
            "P04": {"occupied": False, "distance": 125.0},
        }

    def park_car(self, slot_id: str, final_distance: float = 18.5, smooth_transition: bool = False):
        """Mô phỏng xe tiến vào ô đỗ (khoảng cách giảm dần từ ~120cm xuống ~18cm)."""
        if slot_id not in self.slots:
            return

        if smooth_transition:
            steps = [85.0, 50.0, 28.0, final_distance]
            for d in steps:
                self.slots[slot_id]["distance"] = d
                self.slots[slot_id]["occupied"] = (d < 30.0)
                self.send_telemetry()
                time.sleep(0.3)
        else:
            self.slots[slot_id]["occupied"] = True
            self.slots[slot_id]["distance"] = final_distance

        print(f"[MOCK ESP32] Xe đã đỗ hoàn tất tại ô {slot_id} (Khoảng cách: {final_distance} cm)")

    def leave_car(self, slot_id: str, smooth_transition: bool = False):
        """Mô phỏng xe lùi ra khỏi ô đỗ (khoảng cách tăng dần lên ~120cm)."""
        if slot_id not in self.slots:
            return

        if smooth_transition:
            steps = [35.0, 70.0, 105.0, 120.0]
            for d in steps:
                self.slots[slot_id]["distance"] = d
                self.slots[slot_id]["occupied"] = (d < 30.0)
                self.send_telemetry()
                time.sleep(0.3)
        else:
            self.slots[slot_id]["occupied"] = False
            self.slots[slot_id]["distance"] = 120.0

        print(f"[MOCK ESP32] Xe đã rời khỏi ô {slot_id} (Khoảng cách: 120 cm - EMPTY)")

    def send_telemetry(self) -> bool:
        url = f"{self.base_url}/telemetry/sensors"
        readings = []
        for slot_id, state in self.slots.items():
            # Thêm nhiễu ngẫu nhiên nhỏ +/- 0.4 cm như phần cứng thật
            jitter = random.uniform(-0.4, 0.4)
            readings.append({
                "slot_id": slot_id,
                "distance_cm": round(state["distance"] + jitter, 1),
                "occupied": state["occupied"]
            })

        payload = {
            "device_id": self.device_id,
            "readings": readings
        }

        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                print(f"[MOCK ESP32 -> BACKEND] Telemetry: {[(r['slot_id'], f'{r[\"distance_cm\"]}cm', 'OCC' if r['occupied'] else 'EMPTY') for r in readings]}")
                return True
            else:
                print(f"[MOCK ESP32 ERROR] Server responded with code {resp.status_code}")
                return False
        except Exception as e:
            print(f"[MOCK ESP32 ERROR] Failed to send telemetry: {e}")
            return False

    def run_auto_traffic(self, interval_seconds: float = 3.0, iterations: int = 10):
        """Tự động sinh lưu lượng xe ra vào ngẫu nhiên cho buổi demo/kiểm thử lab."""
        print(f"\n--- Bắt đầu chế độ Auto Traffic (Sinh lưu lượng xe tự động, chu kỳ {interval_seconds}s) ---")
        slot_keys = list(self.slots.keys())
        for i in range(iterations):
            target_slot = random.choice(slot_keys)
            is_currently_occupied = self.slots[target_slot]["occupied"]
            if is_currently_occupied:
                print(f"\n[AUTO-TRAFFIC #{i+1}] Xe chuẩn bị rời khỏi ô {target_slot}...")
                self.leave_car(target_slot, smooth_transition=True)
            else:
                print(f"\n[AUTO-TRAFFIC #{i+1}] Xe mới tiến vào đỗ tại ô {target_slot}...")
                self.park_car(target_slot, final_distance=round(random.uniform(15.0, 22.0), 1), smooth_transition=True)

            self.send_telemetry()
            time.sleep(interval_seconds)
        print("--- Hoàn tất chuỗi Auto Traffic ---")

    def run_loop(self, interval_seconds: float = 2.0, max_ticks: int = None):
        print(f"Starting Mock ESP32 telemetry loop (Interval: {interval_seconds}s)...")
        tick = 0
        try:
            while max_ticks is None or tick < max_ticks:
                self.send_telemetry()
                time.sleep(interval_seconds)
                tick += 1
        except KeyboardInterrupt:
            print("\nMock ESP32 loop stopped by user.")

def main():
    parser = argparse.ArgumentParser(description="Mock ESP32 Telemetry Generator")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Backend API URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Telemetry interval in seconds")
    parser.add_argument("--once", action="store_true", help="Send telemetry once and exit")
    parser.add_argument("--park", choices=["P01", "P02", "P03", "P04"], help="Simulate car parking at slot")
    parser.add_argument("--leave", choices=["P01", "P02", "P03", "P04"], help="Simulate car leaving slot")
    parser.add_argument("--smooth", action="store_true", help="Use gradual distance transitions")
    parser.add_argument("--traffic", action="store_true", help="Run auto traffic simulation loop")

    args = parser.parse_args()
    esp = MockESP32(base_url=args.url)

    if args.traffic:
        esp.run_auto_traffic(interval_seconds=args.interval)
        return

    if args.park:
        esp.park_car(args.park, smooth_transition=args.smooth)
    if args.leave:
        esp.leave_car(args.leave, smooth_transition=args.smooth)

    if args.once or args.park or args.leave:
        esp.send_telemetry()
    else:
        esp.run_loop(interval_seconds=args.interval)

if __name__ == "__main__":
    main()
