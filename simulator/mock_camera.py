"""
MOCK CAMERA — Giả lập camera AI nhận diện 4 vùng đỗ (ROI P01..P04).
Tạo dữ liệu nhận diện trạng thái thị giác và đẩy về Backend.
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

class MockCamera:
    def __init__(self, base_url: str = DEFAULT_BACKEND_URL, camera_id: str = "CAM_MAIN_01"):
        self.base_url = base_url
        self.camera_id = camera_id
        self.slots = {
            "P01": {"state": "EMPTY", "confidence": 0.96},
            "P02": {"state": "EMPTY", "confidence": 0.98},
            "P03": {"state": "EMPTY", "confidence": 0.95},
            "P04": {"state": "EMPTY", "confidence": 0.97},
        }

    def set_slot(self, slot_id: str, state: str, confidence: float = 0.95):
        if slot_id in self.slots:
            self.slots[slot_id] = {"state": state.upper(), "confidence": confidence}
            print(f"[MOCK CAMERA] Slot {slot_id} set to {state.upper()} (conf: {confidence})")

    def send_occupancy(self) -> bool:
        url = f"{self.base_url}/vision/occupancy"
        payload = {
            "camera_id": self.camera_id,
            "slots": [
                {"slot_id": s_id, "state": data["state"], "confidence": data["confidence"]}
                for s_id, data in self.slots.items()
            ]
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                print(f"[MOCK CAMERA -> BACKEND] Vision occupancy sent: {[(s['slot_id'], s['state']) for s in payload['slots']]}")
                return True
            else:
                print(f"[MOCK CAMERA ERROR] Server responded with code {resp.status_code}")
                return False
        except Exception as e:
            print(f"[MOCK CAMERA ERROR] Failed to send vision data: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Mock Camera Occupancy Generator")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Backend API URL")
    parser.add_argument("--set", nargs=2, metavar=("SLOT", "STATE"), help="Set slot state (e.g., --set P01 OCCUPIED)")
    parser.add_argument("--once", action="store_true", help="Send occupancy once and exit")

    args = parser.parse_args()
    cam = MockCamera(base_url=args.url)

    if args.set:
        cam.set_slot(args.set[0], args.set[1])

    cam.send_occupancy()

if __name__ == "__main__":
    main()
