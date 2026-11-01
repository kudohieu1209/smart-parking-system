"""
OCCUPANCY DETECTOR INTERFACE & BASELINE IMPLEMENTATION
Định nghĩa interface nhận diện trạng thái ô đỗ (EMPTY / OCCUPIED / UNKNOWN).

LƯU Ý: Đây là thuật toán cơ sở (Baseline / Heuristic Stub) phục vụ Giai đoạn 1.
Chưa thể xem là mô hình AI chính xác tuyệt đối khi chưa có tập dữ liệu thực tế.
Kiến trúc này sẵn sàng để thay thế bằng YOLOv8 / CNN khi có dữ liệu bãi xe thực tế.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
import cv2

@dataclass
class SlotOccupancyResult:
    slot_id: str
    state: str  # EMPTY, OCCUPIED, UNKNOWN
    confidence: float
    debug_metrics: dict

class OccupancyDetectorBase(ABC):
    @abstractmethod
    def detect_slot(self, slot_id: str, patch: np.ndarray) -> SlotOccupancyResult:
        pass

    def detect_all(self, patches: dict[str, np.ndarray]) -> dict[str, SlotOccupancyResult]:
        results = {}
        for slot_id, patch in patches.items():
            results[slot_id] = self.detect_slot(slot_id, patch)
        return results

class BaselineHeuristicDetector(OccupancyDetectorBase):
    """
    Thuật toán phân tích cơ sở dựa trên:
    - Độ lệch chuẩn màu (Standard Deviation)
    - Mật độ cạnh Canny (Edge Density)
    Khi có xe đỗ, kết cấu bề mặt có độ biến thiên màu và mật độ cạnh cao hơn mặt đường trống.
    """
    def __init__(self, edge_threshold: float = 0.045, std_threshold: float = 52.0):
        self.edge_threshold = edge_threshold
        self.std_threshold = std_threshold

    def detect_slot(self, slot_id: str, patch: np.ndarray) -> SlotOccupancyResult:
        if patch is None or patch.size == 0:
            return SlotOccupancyResult(slot_id=slot_id, state="UNKNOWN", confidence=0.0, debug_metrics={})

        # 1. Chuyển sang ảnh xám
        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

        # 2. Tính độ lệch chuẩn cường độ sáng
        std_val = float(np.std(gray))

        # 3. Tính mật độ cạnh Canny
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges) / edges.size)

        # Quyết định trạng thái: ô đỗ có xe khi mật độ cạnh vượt ngưỡng hoặc độ biến thiên lớn
        is_occupied = (edge_density > self.edge_threshold) and (std_val > self.std_threshold)
        state = "OCCUPIED" if is_occupied else "EMPTY"
        
        # Độ tin cậy ước lượng từ độ tách biệt ngưỡng
        if is_occupied:
            confidence = min(0.99, max(0.65, edge_density / (self.edge_threshold * 1.5)))
        else:
            confidence = min(0.99, max(0.65, 1.0 - (edge_density / (self.edge_threshold * 1.5))))

        return SlotOccupancyResult(
            slot_id=slot_id,
            state=state,
            confidence=round(confidence, 2),
            debug_metrics={"std_val": round(std_val, 2), "edge_density": round(edge_density, 4)}
        )

