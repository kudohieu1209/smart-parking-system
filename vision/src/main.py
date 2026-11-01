"""
VISION MODULE MAIN RUNNER
Đọc khung hình -> Trích xuất 4 ROI -> Phân tích trạng thái -> Đẩy kết quả về Backend.
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
from vision.src.camera_stream import SyntheticCameraStream, OpenCVDeviceStream, OpenCVFileStream
from vision.src.roi_manager import ROIManager
from vision.src.occupancy_detector import BaselineHeuristicDetector

DEFAULT_BACKEND_URL = "http://localhost:8000/api/v1"

def run_vision_loop(
    source_type: str = "synthetic",
    source_path: str = None,
    backend_url: str = DEFAULT_BACKEND_URL,
    interval_seconds: float = 2.0,
    max_frames: int = None
):
    print(f"[VISION SERVICE] Khởi động module Thị giác máy tính (Source: {source_type})...")

    # 1. Khởi tạo Stream
    if source_type == "synthetic":
        stream = SyntheticCameraStream()
    elif source_type == "video":
        stream = OpenCVFileStream(source_path)
    elif source_type == "device":
        device_id = int(source_path) if source_path and source_path.isdigit() else 0
        stream = OpenCVDeviceStream(device_id)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    if not stream.open():
        print(f"[VISION ERROR] Không thể mở nguồn video: {source_type}")
        return

    # 2. Khởi tạo ROI Manager & Detector
    roi_manager = ROIManager()
    detector = BaselineHeuristicDetector()

    frame_count = 0
    try:
        while max_frames is None or frame_count < max_frames:
            ret, frame = stream.read_frame()
            if not ret or frame is None:
                print("[VISION] Không đọc được khung hình, kết thúc.")
                break

            # Cắt 4 patches từ ROI
            patches = roi_manager.extract_slot_patches(frame)
            # Nhận diện trạng thái
            results = detector.detect_all(patches)

            # Đóng gói và gửi về backend
            payload = {
                "camera_id": "CAM_MAIN_01",
                "slots": [
                    {
                        "slot_id": r.slot_id,
                        "state": r.state,
                        "confidence": r.confidence
                    }
                    for r in results.values()
                ]
            }

            try:
                resp = requests.post(f"{backend_url}/vision/occupancy", json=payload, timeout=3)
                print(f"[VISION -> BACKEND] Frame {frame_count+1}: {[(r.slot_id, r.state, f'{int(r.confidence*100)}%') for r in results.values()]} -> HTTP {resp.status_code}")
            except Exception as e:
                print(f"[VISION WARNING] Không thể kết nối Backend ({e})")

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                break
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n[VISION] Đã dừng theo yêu cầu người dùng.")
    finally:
        stream.release()
        print("[VISION] Đã giải phóng tài nguyên Camera Stream.")

def main():
    parser = argparse.ArgumentParser(description="Smart Parking Computer Vision Module")
    parser.add_argument("--source", choices=["synthetic", "device", "video"], default="synthetic", help="Video source type")
    parser.add_argument("--path", help="Path to video file or webcam device index")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Backend API URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Process interval in seconds")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to process (None = run forever)")

    args = parser.parse_args()
    run_vision_loop(
        source_type=args.source,
        source_path=args.path,
        backend_url=args.url,
        interval_seconds=args.interval,
        max_frames=args.frames
    )

if __name__ == "__main__":
    main()
