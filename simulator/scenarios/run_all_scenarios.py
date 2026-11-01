"""
BỘ CHẠY TỔNG HỢP TOÀN BỘ CÁC KỊCH BẢN KIỂM THỬ (TEST SCENARIO RUNNER)
Thực thi tuần tự 5 kịch bản mô phỏng nâng cao và xuất báo cáo nghiệm thu:
1. scenario_1_normal_flow: Quy trình xe vào/ra tiêu chuẩn
2. scenario_2_parking_full: Xử lý từ chối khi bãi đã đầy 4/4 ô
3. scenario_3_invalid_rfid: Thẻ lạ, thẻ khóa, Anti-passback, chưa check-in
4. scenario_4_sensor_camera_mismatch: Phát hiện & xử lý sai lệch cảm biến vs camera
5. scenario_5_barrier_safety: Khóa liên động bảo vệ khi có vật cản dưới barrier
"""

import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from simulator.scenarios import scenario_1_normal_flow
from simulator.scenarios import scenario_2_parking_full
from simulator.scenarios import scenario_3_invalid_rfid
from simulator.scenarios import scenario_4_sensor_camera_mismatch
from simulator.scenarios import scenario_5_barrier_safety

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"

    print("\n" + "#"*80)
    print("   HỆ THỐNG KIỂM THỬ TOÀN DIỆN CHẾ ĐỘ FULL SOFTWARE SIMULATION")
    print("   SMART PARKING SYSTEM — LAB AUTOMATION SUITE")
    print("#"*80)

    scenarios = [
        ("Kịch bản 1: Quy trình xe vào/ra bãi tiêu chuẩn (Normal Flow)", scenario_1_normal_flow.run_test),
        ("Kịch bản 2: Xử lý từ chối khi bãi đỗ xe đã đầy (Parking Full)", scenario_2_parking_full.run_test),
        ("Kịch bản 3: Kiểm soát thẻ RFID không hợp lệ & Anti-passback", scenario_3_invalid_rfid.run_test),
        ("Kịch bản 4: Động cơ phát hiện sai lệch Cảm biến vs Camera (Mismatch)", scenario_4_sensor_camera_mismatch.run_test),
        ("Kịch bản 5: Khóa liên động an toàn Barrier khi có vật cản (Safety Interlock)", scenario_5_barrier_safety.run_test),
    ]

    results = []
    total_start = time.time()

    for idx, (title, run_func) in enumerate(scenarios, 1):
        start_t = time.time()
        try:
            passed = run_func(base_url)
            elapsed = time.time() - start_t
            results.append((idx, title, "PASSED", f"{elapsed:.2f}s", None))
        except Exception as e:
            elapsed = time.time() - start_t
            results.append((idx, title, "FAILED", f"{elapsed:.2f}s", str(e)))

    total_elapsed = time.time() - total_start

    # Xuất bảng tổng hợp kết quả
    print("\n\n" + "="*85)
    print("              BÁO CÁO TỔNG HỢP KẾT QUẢ KIỂM THỬ MÔ PHỎNG (E2E REPORT)        ")
    print("="*85)
    print(f"{'STT':<5} | {'Tên Kịch Bản Kiểm Thử':<58} | {'Kết Quả':<8} | {'Thời Gian'}")
    print("-"*85)

    all_passed = True
    for idx, title, status, elapsed, err in results:
        status_display = "[OK] PASS" if status == "PASSED" else "[!] FAIL"
        print(f"{idx:<5} | {title:<58} | {status_display:<8} | {elapsed}")
        if status != "PASSED":
            all_passed = False
            print(f"      -> Chi tiết lỗi: {err}")

    print("-"*85)
    print(f"Tổng thời gian kiểm thử: {total_elapsed:.2f} giây.")
    if all_passed:
        print("TẤT CẢ 5/5 KỊCH BẢN MÔ PHỎNG ĐÃ VƯỢT QUA 100%! HỆ THỐNG HOẠT ĐỘNG HOÀN HẢO.")
    else:
        print("MỘT SỐ KỊCH BẢN CHƯA ĐẠT. VUI LÒNG KIỂM TRA LẠI CHI TIẾT LỖI Ở TRÊN.")
    print("="*85 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
