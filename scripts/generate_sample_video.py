"""
TẠO VIDEO MẪU VÀ FRAME MẪU CHO MODULE CAMERA (SAMPLE VIDEO GENERATOR)
Tạo file video MP4 'vision/samples/sample_parking.mp4' và các ảnh mẫu:
- frame_empty.jpg
- frame_p01_occupied.jpg
- frame_all_occupied.jpg
"""

import os
import sys
import numpy as np
import cv2

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def draw_parking_lot(width=640, height=480, occupied_slots=None):
    if occupied_slots is None:
        occupied_slots = []

    frame = np.full((height, width, 3), 45, dtype=np.uint8)

    # Vạch sơn đường
    cv2.line(frame, (20, 360), (620, 360), (220, 220, 220), 2)
    cv2.putText(frame, "LANE DIRECTION >>>", (220, 395), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

    slot_coords = {
        "P01": (40, 100, 120, 240),
        "P02": (180, 100, 120, 240),
        "P03": (340, 100, 120, 240),
        "P04": (480, 100, 120, 240),
    }

    colors = {
        "P01": (180, 60, 50),   # Đỏ
        "P02": (50, 140, 200),  # Cam
        "P03": (60, 180, 70),   # Xanh lá
        "P04": (180, 50, 180),  # Tím
    }

    for slot_id, (x, y, w, h) in slot_coords.items():
        # Vẽ viền ô đỗ
        is_occ = slot_id in occupied_slots
        border_color = (0, 0, 220) if is_occ else (255, 255, 255)
        cv2.rectangle(frame, (x, y), (x + w, y + h), border_color, 2)
        cv2.putText(frame, slot_id, (x + 35, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if is_occ:
            car_x = x + 15
            car_y = y + 25
            car_w = w - 30
            car_h = h - 50
            car_color = colors.get(slot_id, (180, 50, 40))
            cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), car_color, -1)
            cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), (255, 255, 255), 2)
            cv2.rectangle(frame, (car_x + 5, car_y + 30), (car_x + car_w - 5, car_y + 80), (230, 210, 180), -1)
            cv2.circle(frame, (car_x + 10, car_y + 10), 5, (0, 255, 255), -1)
            cv2.circle(frame, (car_x + car_w - 10, car_y + 10), 5, (0, 255, 255), -1)

    return frame

def main():
    samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vision", "samples")
    os.makedirs(samples_dir, exist_ok=True)

    print(f"Đang sinh dữ liệu mẫu tại: {samples_dir}...")

    # 1. Lưu các ảnh tĩnh mẫu (Sample Frames)
    empty_frame = draw_parking_lot(occupied_slots=[])
    cv2.imwrite(os.path.join(samples_dir, "frame_empty.jpg"), empty_frame)

    p01_frame = draw_parking_lot(occupied_slots=["P01"])
    cv2.imwrite(os.path.join(samples_dir, "frame_p01_occupied.jpg"), p01_frame)

    all_frame = draw_parking_lot(occupied_slots=["P01", "P02", "P03", "P04"])
    cv2.imwrite(os.path.join(samples_dir, "frame_all_occupied.jpg"), all_frame)

    print(" -> Đã tạo 3 ảnh tĩnh: frame_empty.jpg, frame_p01_occupied.jpg, frame_all_occupied.jpg")

    # 2. Sinh video MP4 (Sample Video - 120 frames @ 10fps = 12s)
    video_path = os.path.join(samples_dir, "sample_parking.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 10.0, (640, 480))

    for frame_idx in range(120):
        # Kịch bản theo thời gian:
        # Frame 0..29: Bãi trống
        # Frame 30..59: Xe vào ô P01
        # Frame 60..89: Xe vào tiếp ô P03
        # Frame 90..119: Xe P01 rời ô, chỉ còn P03
        if frame_idx < 30:
            occ = []
            status_text = "SCENARIO: All 4 slots EMPTY"
        elif frame_idx < 60:
            occ = ["P01"]
            status_text = "SCENARIO: Car entered P01"
        elif frame_idx < 90:
            occ = ["P01", "P03"]
            status_text = "SCENARIO: Car entered P03 (P01, P03 OCCUPIED)"
        else:
            occ = ["P03"]
            status_text = "SCENARIO: Car left P01 (Only P03 OCCUPIED)"

        frame = draw_parking_lot(occupied_slots=occ)
        cv2.putText(frame, f"{status_text} [Frame {frame_idx}/120]", (10, 465),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)
        out.write(frame)

    out.release()
    print(f" -> Đã tạo file video MP4 mẫu thành công: {video_path}")

if __name__ == "__main__":
    main()
