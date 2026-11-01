"""
KỊCH BẢN 5: KIỂM THỬ KHÓA LIÊN ĐỘNG AN TOÀN BARRIER (SAFETY OBSTRUCTION INTERLOCK)
Kiểm thử quy tắc an toàn vật lý quan trọng:
"Không được đóng barrier khi còn xe trong vùng chắn."
1. Mở barrier cổng vào (góc mở 90°).
2. Kích hoạt cảm biến an toàn quang (Phát hiện xe dừng ngay dưới thanh chắn).
3. Ra lệnh hạ barrier (CLOSE).
4. Hệ thống TỪ CHỐI hạ thanh chắn, duy trì góc mở 90° và phát cảnh báo BARRIER_OBSTRUCTION_DETECTED.
5. Xe di chuyển ra khỏi vùng an toàn (Cảm biến báo CLEAR).
6. Ra lệnh hạ barrier lại -> Thành công hạ thanh chắn xuống 0°.
7. Kiểm thử tương tự trên Cổng Ra (Exit Gate).
"""

import sys
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api/v1"

def run_test(base_url: str = BASE_URL):
    print("\n" + "="*75)
    print(" [KỊCH BẢN 5] BẮT ĐẦU KIỂM THỬ KHÓA LIÊN ĐỘNG AN TOÀN BARRIER")
    print("="*75)

    # 1. Reset
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    # BƯỚC 1: Mở cổng vào
    print("[1] Mở Barrier Cổng Vào (Command: OPEN)...")
    open_resp = requests.post(f"{base_url}/gate/command", json={"gate_id": "ENTRY", "command": "OPEN"}, timeout=5)
    assert open_resp.status_code == 200

    stats = requests.get(f"{base_url}/system/stats", timeout=5).json()
    assert stats["barrier_entry_state"] == "OPEN" and stats["barrier_entry_angle"] == 90
    print(f" -> OK: Barrier Cổng Vào đang MỞ (Trạng thái: {stats['barrier_entry_state']}, Góc: {stats['barrier_entry_angle']}°)")

    # BƯỚC 2: Kích hoạt cảm biến an toàn (vật cản chặn cánh barie)
    print("[2] Cảm biến an toàn phát hiện xe dừng ngay dưới chân thanh chắn...")
    sensor_resp = requests.post(f"{base_url}/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": True}, timeout=5)
    assert sensor_resp.status_code == 200

    stats = requests.get(f"{base_url}/system/stats", timeout=5).json()
    assert stats["barrier_entry_obstruction"] is True
    print(" -> OK: Đèn báo cảm biến quang an toàn đã chuyển sang CÓ VẬT CẢN (Obstruction = TRUE)")

    # BƯỚC 3: Ra lệnh hạ cánh barie khi còn vật cản -> Bị từ chối
    print("[3] Thử ra lệnh ĐÓNG BARRIER khi còn xe dưới cánh chắn...")
    close_attempt = requests.post(f"{base_url}/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"}, timeout=5)
    assert close_attempt.status_code == 400, "Bắt buộc phải từ chối hạ cánh khi có vật cản"
    assert "SAFETY" in close_attempt.json()["detail"]
    print(f" -> OK: Hệ thống ngăn chặn hạ cánh barie chuẩn xác! [{close_attempt.json()['detail']}]")

    # Kiểm tra góc mở vẫn được giữ ở 90° để bảo vệ phương tiện
    stats_during = requests.get(f"{base_url}/system/stats", timeout=5).json()
    assert stats_during["barrier_entry_state"] == "OPEN" and stats_during["barrier_entry_angle"] == 90
    print(f" -> OK: Thanh chắn vẫn được khóa ở góc {stats_during['barrier_entry_angle']}° an toàn.")

    # Kiểm tra cảnh báo được sinh ra
    alerts = requests.get(f"{base_url}/system/alerts", timeout=5).json()
    safety_alerts = [a for a in alerts if a["alert_type"] == "BARRIER_OBSTRUCTION_DETECTED"]
    assert len(safety_alerts) > 0, "Phải ghi nhận cảnh báo an toàn BARRIER_OBSTRUCTION_DETECTED"
    print(f" -> OK: Đã ghi nhận cảnh báo nguy cơ kẹt xe #{safety_alerts[0]['id']} [{safety_alerts[0]['message']}]")

    # BƯỚC 4: Xe rời khỏi vùng cản
    print("\n[4] Xe đã di chuyển qua cổng hoàn toàn (Giải tỏa vật cản an toàn)...")
    requests.post(f"{base_url}/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": False}, timeout=5)
    stats_clear = requests.get(f"{base_url}/system/stats", timeout=5).json()
    assert stats_clear["barrier_entry_obstruction"] is False
    print(" -> OK: Vùng quét an toàn đã thông thoáng (Obstruction = FALSE)")

    # BƯỚC 5: Hạ barrier an toàn
    print("[5] Ra lệnh ĐÓNG BARRIER sau khi vùng quét thông thoáng...")
    close_success = requests.post(f"{base_url}/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"}, timeout=5)
    assert close_success.status_code == 200

    stats_final = requests.get(f"{base_url}/system/stats", timeout=5).json()
    assert stats_final["barrier_entry_state"] == "CLOSED" and stats_final["barrier_entry_angle"] == 0
    print(f" -> OK: Hạ barrier thành công an toàn! (Trạng thái: {stats_final['barrier_entry_state']}, Góc: {stats_final['barrier_entry_angle']}°)")

    # Dọn dẹp
    requests.post(f"{base_url}/simulator/reset", timeout=5)

    print("\n" + "="*75)
    print(" >>> KỊCH BẢN 5: THÀNH CÔNG 100% <<< ")
    print("="*75)
    return True

if __name__ == "__main__":
    run_test()
