"""
CAMERA STREAM INTERFACE — Giao diện trích xuất khung hình từ Camera/Video/Giả lập đồ hoạ.
"""

from abc import ABC, abstractmethod
import time
import numpy as np
import cv2

class CameraStreamBase(ABC):
    @abstractmethod
    def open(self) -> bool:
        pass

    @abstractmethod
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        pass

    @abstractmethod
    def release(self):
        pass

class SyntheticCameraStream(CameraStreamBase):
    """
    Tạo luồng hình ảnh nhân tạo 640x480 mô phỏng bãi đỗ xe 4 ô.
    Cho phép kiểm thử thị giác máy tính mà không cần webcam vật lý.
    """
    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.occupied_slots: set[str] = set()
        self.is_open = False

    def open(self) -> bool:
        self.is_open = True
        return True

    def set_slot_car(self, slot_id: str, has_car: bool):
        if has_car:
            self.occupied_slots.add(slot_id)
        else:
            self.occupied_slots.discard(slot_id)

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if not self.is_open:
            return False, None

        # Nền bãi đỗ nhựa đường xám đậm
        frame = np.full((self.height, self.width, 3), 45, dtype=np.uint8)

        # Vẽ vạch kẻ đường và vạch sơn bãi đỗ
        cv2.line(frame, (20, 360), (620, 360), (220, 220, 220), 2)
        cv2.putText(frame, "LANE DIRECTION >>>", (220, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

        slot_coords = {
            "P01": (40, 100, 120, 240),
            "P02": (180, 100, 120, 240),
            "P03": (340, 100, 120, 240),
            "P04": (480, 100, 120, 240),
        }

        for slot_id, (x, y, w, h) in slot_coords.items():
            # Vẽ viền ô đỗ (màu trắng)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
            cv2.putText(frame, slot_id, (x + 35, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Nếu ô có xe -> vẽ hình xe hơi mô phỏng (hình chữ nhật có kính và mui)
            if slot_id in self.occupied_slots:
                car_x = x + 15
                car_y = y + 25
                car_w = w - 30
                car_h = h - 50
                # Thân xe (màu xanh dương đậm)
                cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), (180, 50, 40), -1)
                cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), (220, 100, 80), 2)
                # Kính chắn gió
                cv2.rectangle(frame, (car_x + 5, car_y + 30), (car_x + car_w - 5, car_y + 80), (230, 210, 180), -1)
                # Đèn xe
                cv2.circle(frame, (car_x + 10, car_y + 10), 5, (0, 255, 255), -1)
                cv2.circle(frame, (car_x + car_w - 10, car_y + 10), 5, (0, 255, 255), -1)

        # Timestamp góc dưới
        ts_text = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"CAM_01 SYNTHETIC [MOCK] - {ts_text}", (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)

        return True, frame

    def release(self):
        self.is_open = False

class OpenCVDeviceStream(CameraStreamBase):
    """Đọc khung hình từ USB Webcam thật."""
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.device_index)
        return self.cap.isOpened()

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if not self.cap or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()

# Global Camera Service for Live Streaming
import os
_global_stream: CameraStreamBase | None = None

def get_shared_stream(source: str = "synthetic", path: str = None) -> CameraStreamBase:
    global _global_stream
    if _global_stream is None:
        sample_mp4 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "sample_parking.mp4")
        if source == "video" and path and os.path.exists(path):
            _global_stream = OpenCVFileStream(path)
        elif os.path.exists(sample_mp4):
            _global_stream = OpenCVFileStream(sample_mp4)
        else:
            _global_stream = SyntheticCameraStream()
        _global_stream.open()
    return _global_stream

def get_latest_jpeg_frame(draw_roi: bool = True) -> bytes | None:
    from vision.src.roi_manager import ROIManager
    stream = get_shared_stream()
    ret, frame = stream.read_frame()
    if not ret or frame is None:
        return None
    annotated = frame.copy()
    if draw_roi:
        roi_mgr = ROIManager()
        for slot_id, roi in roi_mgr.slots_roi.items():
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 255), 1)
            cv2.putText(annotated, f"ROI: {slot_id}", (x + 5, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    ret, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ret:
        return jpeg.tobytes()
    return None


class OpenCVFileStream(CameraStreamBase):
    """Đọc khung hình từ file video mp4 đã ghi sẵn."""
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.video_path)
        return self.cap.isOpened()

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if not self.cap or not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            # Quay lại đầu video (loop)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        if self.cap:
            self.cap.release()

# Global Camera Service for Live Streaming
import os
_global_stream: CameraStreamBase | None = None

def get_shared_stream(source: str = "synthetic", path: str = None) -> CameraStreamBase:
    global _global_stream
    if _global_stream is None:
        sample_mp4 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "sample_parking.mp4")
        if source == "video" and path and os.path.exists(path):
            _global_stream = OpenCVFileStream(path)
        elif os.path.exists(sample_mp4):
            _global_stream = OpenCVFileStream(sample_mp4)
        else:
            _global_stream = SyntheticCameraStream()
        _global_stream.open()
    return _global_stream

def get_latest_jpeg_frame(draw_roi: bool = True) -> bytes | None:
    from vision.src.roi_manager import ROIManager
    stream = get_shared_stream()
    ret, frame = stream.read_frame()
    if not ret or frame is None:
        return None
    annotated = frame.copy()
    if draw_roi:
        roi_mgr = ROIManager()
        for slot_id, roi in roi_mgr.slots_roi.items():
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 255), 1)
            cv2.putText(annotated, f"ROI: {slot_id}", (x + 5, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    ret, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ret:
        return jpeg.tobytes()
    return None

