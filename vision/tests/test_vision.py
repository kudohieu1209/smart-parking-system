import os
import pytest
from vision.src.camera_stream import SyntheticCameraStream
from vision.src.roi_manager import ROIManager
from vision.src.occupancy_detector import BaselineHeuristicDetector

def test_synthetic_camera_stream():
    stream = SyntheticCameraStream()
    assert stream.open() is True
    ret, frame = stream.read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    stream.release()

def test_roi_manager_extraction():
    stream = SyntheticCameraStream()
    stream.open()
    ret, frame = stream.read_frame()
    
    roi_mgr = ROIManager()
    patches = roi_mgr.extract_slot_patches(frame)
    assert len(patches) == 4
    assert "P01" in patches
    assert "P04" in patches
    assert patches["P01"].shape[0] > 0
    assert patches["P01"].shape[1] > 0
    stream.release()

def test_baseline_detector_empty_and_occupied():
    stream = SyntheticCameraStream()
    stream.open()
    roi_mgr = ROIManager()
    detector = BaselineHeuristicDetector()

    # 1. Ban đầu cả 4 ô trống
    _, empty_frame = stream.read_frame()
    patches_empty = roi_mgr.extract_slot_patches(empty_frame)
    results_empty = detector.detect_all(patches_empty)
    for s_id in ["P01", "P02", "P03", "P04"]:
        assert results_empty[s_id].state == "EMPTY"

    # 2. Đặt xe vào ô P01 trên synthetic stream
    stream.set_slot_car("P01", True)
    _, occupied_frame = stream.read_frame()
    patches_occ = roi_mgr.extract_slot_patches(occupied_frame)
    results_occ = detector.detect_all(patches_occ)
    assert results_occ["P01"].state == "OCCUPIED"
    assert results_occ["P02"].state == "EMPTY"

    # 3. Test overlay drawing
    annotated = roi_mgr.draw_overlays(occupied_frame, {k: {"state": v.state, "confidence": v.confidence} for k, v in results_occ.items()})
    assert annotated.shape == occupied_frame.shape

    stream.release()
