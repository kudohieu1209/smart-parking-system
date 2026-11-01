"""
ROI MANAGER — Quản lý và xử lý 4 vùng đỗ xe (Region of Interest P01..P04).
"""

import json
import os
import numpy as np
import cv2

class ROIManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to vision/config/roi_config.json relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "roi_config.json")

        self.config_path = config_path
        self.slots_roi: dict[str, dict] = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"ROI config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.slots_roi = data.get("slots", {})

    def extract_slot_patches(self, frame: np.ndarray) -> dict[str, np.ndarray]:
        """Cắt ảnh con tương ứng với từng ô đỗ."""
        patches = {}
        for slot_id, roi in self.slots_roi.items():
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            # Đảm bảo toạ độ không vượt quá kích thước frame
            h_max, w_max = frame.shape[:2]
            y2 = min(y + h, h_max)
            x2 = min(x + w, w_max)
            patches[slot_id] = frame[y:y2, x:x2]
        return patches

    def draw_overlays(self, frame: np.ndarray, occupancy_results: dict[str, dict]) -> np.ndarray:
        """Vẽ viền ROI và nhãn trạng thái lên khung hình hiển thị."""
        annotated = frame.copy()
        for slot_id, roi in self.slots_roi.items():
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            res = occupancy_results.get(slot_id, {"state": "UNKNOWN", "confidence": 0.0})
            state = res.get("state", "UNKNOWN")
            conf = res.get("confidence", 0.0)

            # Màu viền: Đỏ nếu có xe (OCCUPIED), Xanh lá nếu trống (EMPTY), Xám nếu UNKNOWN
            if state == "OCCUPIED":
                color = (0, 0, 230)  # Đỏ (BGR)
            elif state == "EMPTY":
                color = (0, 220, 0)  # Xanh lá
            else:
                color = (180, 180, 180)

            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            label = f"{slot_id}: {state} ({int(conf * 100)}%)"
            cv2.putText(annotated, label, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        return annotated
