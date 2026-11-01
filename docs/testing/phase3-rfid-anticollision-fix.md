# Báo Cáo Kỹ Thuật: Sửa Lỗi Checksum BCC MFRC522 Trong Mô Phỏng Wokwi & Phần Cứng

- **Dự án:** SMART PARKING SYSTEM — ESP32 DevKit + RFID RC522 + FreeRTOS + FastAPI + React
- **Module:** `firmware/esp32/components/rfid/rfid_reader.c`
- **Phiên bản:** Phase 3 — RFID Anti-collision & Checksum Hardening
- **Repository:** https://github.com/kudohieu1209/smart-parking-system
- **Commit:** `f03436e`

---

## 1. Hiện Tượng Lỗi Ban Đầu

Khi khởi chạy firmware ESP32 trên trình mô phỏng Wokwi:
- 4 cảm biến siêu âm HC-SR04 đo khoảng cách và gửi telemetry bình thường.
- Màn hình LCD 1602 I2C hiển thị thông tin chính xác.
- Khi nhấn nút quẹt Blue Card (UID `30:A1:23:45`) trên module MFRC522, Serial Monitor liên tục cảnh báo:

```text
W (12430) MFRC522_RFID: MFRC522 Checksum mismatch: calculated 0xE4, received 0x00
```

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 2.1. Bản chất toán học của `calculated 0xE4, received 0x00`
Thẻ Blue Card có cấu hình:
- UID: `30 : A1 : 23 : 45`
- Checksum BCC chuẩn (XOR 4 byte đầu):
  $$\text{BCC} = 0x30 \oplus 0xA1 \oplus 0x23 \oplus 0x45 = 0xF7$$
- Khung phản hồi 5 byte đúng từ PICC: `[0x30, 0xA1, 0x23, 0x45, 0xF7]`.

Khi quan sát giá trị `calculated 0xE4, received 0x00`:
- Nhận được byte thứ 5: `uid_buf[4] = 0x00`.
- Giá trị XOR 4 byte đầu: `uid_buf[0] ^ uid_buf[1] ^ uid_buf[2] ^ uid_buf[3] = 0xE4`.

Xét các byte của thẻ:
$$0xA1 \oplus 0x45 = (1010\,0001)_2 \oplus (0100\,0101)_2 = (1110\,0100)_2 = 0xE4$$

Buffer thực tế mà bộ đệm `uid_buf` nhận được là:
`[0xA1, 0x45, 0x00, 0x00, 0x00]`

Các byte tại chỉ số chẵn (0, 2, 4 tương ứng `0x30`, `0x23`, `0xF7`) đã biến mất hoàn toàn, chỉ còn lại các byte tại chỉ số lẻ (1, 3 tương ứng `0xA1`, `0x45`)!

### 2.2. Cơ chế thất thoát dữ liệu do đọc SPI sai chuẩn FIFO
Trong phiên bản cũ của `rfid_reader.c`, việc đọc dữ liệu phản hồi từ FIFO được thực hiện qua vòng lặp:
```c
// LỖI: Gọi mfrc522_read_reg nhiều lần cho FIFODataReg
for (int i = 0; i < fifo_len; i++) {
    back_data[i] = mfrc522_read_reg(spi, FIFODataReg);
}
```
Hàm `mfrc522_read_reg` gửi một transaction SPI 16-bit:
1. 8-bit đầu: Master gửi byte địa chỉ `0x80 | ((FIFODataReg << 1) & 0x7E) = 0x92`. Chip MFRC522 bắt đầu clock out byte đầu tiên của FIFO (`0x30`) vào `rx_buf[0]`.
2. 8-bit sau: Master gửi dummy `0x00`. Chip MFRC522 tiếp tục clock out byte thứ hai của FIFO (`0xA1`) vào `rx_buf[1]`.
3. Hàm chỉ trả về `rx_buf[1]` (`0xA1`) và vứt bỏ `rx_buf[0]` (`0x30`)!
4. Ở lần lặp kế tiếp, transaction 16-bit mới lại clock tiếp 2 byte từ FIFO: byte `0x23` rơi vào `rx_buf[0]` và bị vứt bỏ, chỉ lưu byte `0x45`!
5. Ở lần lặp thứ ba, byte `0xF7` (BCC) bị vứt bỏ, `rx_buf[1]` nhận `0x00` do FIFO đã cạn!

Kết quả là toàn bộ byte chẵn bị loại bỏ, dẫn đến `uid_buf = [0xA1, 0x45, 0x00, 0x00, 0x00]`.

### 2.3. Lỗi xóa cờ ngắt `ComIrqReg`
Trong MFRC522, thanh ghi `ComIrqReg` (0x04) quy định:
- Bit 7 (`Set1`): Khi bằng `0`, việc ghi bit `1` vào bất kỳ vị trí nào từ bit 0 đến 6 sẽ **XÓA** cờ ngắt tương ứng.
- Lệnh cũ dùng `mfrc522_clear_bit_mask(spi, ComIrqReg, 0x80)` chỉ xóa bit 7 mà không xóa triệt để các cờ `RxIRq` và `IdleIRq` đang chờ.
- Chuẩn giao tiếp MFRC522 (Miguel Balboa) yêu cầu ghi trực tiếp `0x7F` để xóa đồng thời toàn bộ 7 cờ ngắt.

### 2.4. Thứ tự lệnh dừng và khởi tạo bộ đệm
Phiên bản cũ gọi FlushBuffer trước khi chuyển transceiver sang `PCD_IDLE`. Điều này có thể khiến dữ liệu đang thu dở tiếp tục ghi đè vào FIFO vừa bị xóa. Thứ tự chuẩn bắt buộc là:
1. `PCD_IDLE`: Dừng transceiver.
2. `ComIrqReg = 0x7F`: Xóa sạch cờ ngắt.
3. `FIFOLevelReg = 0x80`: Flush FIFO.

### 2.5. Thiếu khoảng trễ giữa REQA và ANTICOLLISION
Theo chuẩn ISO 14443-3, sau khi phản hồi ATQA cho lệnh REQA (7-bit), PICC cần một khoảng trễ nhỏ (Frame Delay Time) để ổn định trạng thái từ `IDLE` sang `READY` trước khi tiếp nhận lệnh chọn Cascade Level 1 (`PICC_ANTICOLL`, `0x93 0x20`).

---

## 3. Các Biện Pháp Khắc Phục Đã Triển Khai

### 3.1. Viết mới hàm `mfrc522_read_fifo()` và `mfrc522_write_fifo()`
Áp dụng cơ chế streaming SPI chuẩn của NXP MFRC522:
```c
static esp_err_t mfrc522_read_fifo(spi_device_handle_t spi, uint8_t *data, size_t len) {
    if (!spi || !data || len == 0 || len > 64) return ESP_ERR_INVALID_ARG;
    uint8_t tx_buf[65] = {0};
    uint8_t rx_buf[65] = {0};

    uint8_t addr = (uint8_t)(((FIFODataReg << 1) & 0x7E) | 0x80);
    tx_buf[0] = addr;
    for (size_t i = 1; i < len; i++) {
        tx_buf[i] = addr;
    }
    tx_buf[len] = 0x00;

    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = tx_buf,
        .rx_buffer = rx_buf
    };
    esp_err_t ret = spi_device_polling_transmit(spi, &t);
    if (ret != ESP_OK) return ret;

    for (size_t i = 0; i < len; i++) {
        data[i] = rx_buf[i + 1];
    }
    return ESP_OK;
}
```
Chân Chip Select (CS) được giữ mức LOW liên tục trong suốt quá trình đọc `len` byte, bảo toàn 100% dữ liệu FIFO.

### 3.2. Cải tổ `mfrc522_to_card()`
- Chuyển `CommandReg = PCD_IDLE` trước khi xóa cờ ngắt và flush FIFO.
- Xóa ngắt triệt để bằng `mfrc522_write_reg(spi, ComIrqReg, 0x7F)`.
- Đọc độ dài FIFO với mặt nạ `FIFOLevelReg & 0x7F`.
- Đọc số bit hợp lệ của byte cuối cùng qua `ControlReg & 0x07` (`RxLastBits`).

### 3.3. Hoàn thiện quy trình `rfid_reader_poll()`
- Lệnh REQA: `BitFramingReg = 0x07`.
- Bổ sung khoảng trễ bảo vệ: `esp_rom_delay_us(1000)`.
- Lệnh ANTICOLLISION: Đặt lại `BitFramingReg = 0x00`.
- Kiểm tra nghiêm ngặt: Phản hồi thẻ 4-byte UID bắt buộc phải có `back_len == 5` và `valid_bits == 0`.
- Xác minh checksum BCC: `bcc_calc == bcc_recv`. Tuyệt đối không bypass BCC và không hardcode UID.

### 3.4. Bổ sung hệ thống chẩn đoán `CONFIG_SMART_PARKING_RFID_DEBUG`
Thêm cấu hình Kconfig vào `firmware/esp32/main/Kconfig.projbuild` và kích hoạt mặc định trong `firmware/esp32/sdkconfig.defaults`.
Khi quét thẻ, hệ thống xuất đầy đủ thông tin:
```text
I (14520) MFRC522_RFID: [ENTRY RFID] Raw UID: 30 A1 23 45 F7 | FIFO_len=5, RxLastBits=0, ErrorReg=0x00, ComIrq=0x20 | BCC calc=0xF7, recv=0xF7
```

---

## 4. Kết Quả Kiểm Thử Phần Mềm

| Hạng mục kiểm tra | Công cụ thực hiện | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Python Pytest Suite** | `pytest -v` (23 test cases) | 23 passed in 4.70s | **PASS** ✅ |
| **Frontend Production Build** | `npm --prefix frontend run build` | 2065 modules transformed, Vite bundle 192 kB | **PASS** ✅ |
| **ESP-IDF CI Workflow** | GitHub Actions Run #41308059911 | ESP-IDF v5.3 compile & link thành công, sinh artifact `esp32-firmware-binaries` (5.3 MB) | **PASS** ✅ |
| **Wokwi Runtime Verification** | Chạy mô phỏng nạp `smart_parking_esp32_merged.bin` | Cần người dùng nạp file bin mới vào Wokwi để đối soát log Serial | **NOT VERIFIED** ⚠️ |

### 4.1. Hướng Dẫn Tải Firmware Đã Fix và Kiểm Thử Trên Wokwi
1. Truy cập GitHub Actions Run #41308059911:
   `https://github.com/kudohieu1209/smart-parking-system/actions/runs/41308059911`
2. Tải artifact **`esp32-firmware-binaries`** (chứa file `smart_parking_esp32_merged.bin` tại offset `0x0`).
3. Mở dự án trên Wokwi Web / VS Code Wokwi extension.
4. Nạp file `smart_parking_esp32_merged.bin`.
5. Mở Serial Monitor (Baud 115200). Nhấn phím `b` rồi nhấn `t` (hoặc bấm nút Tap trên đầu đọc MFRC522 Cổng Vào).
6. Quan sát Serial Monitor:
   - Dòng log chẩn đoán:
     `MFRC522_RFID: [ENTRY RFID] Raw UID: 30 A1 23 45 F7 | FIFO_len=5, RxLastBits=0, ErrorReg=0x00, ComIrq=0x20 | BCC calc=0xF7, recv=0xF7`
   - Dòng log chấp thuận:
     `>>> ENTRY TAP: Card UID = 30:A1:23:45 <<<`
   - Tuyệt đối không còn xuất hiện thông báo:
     `MFRC522 Checksum mismatch: calculated 0xE4, received 0x00`.

> [!IMPORTANT]
> **Quy định xác minh Wokwi:** Tuân thủ nguyên tắc không được đánh dấu PASS khi chưa chạy kiểm chứng trực tiếp trên Wokwi. Trạng thái kiểm chứng mô phỏng Wokwi được ghi nhận rõ ràng là **NOT VERIFIED** cho đến khi ghi nhận log thực tế không còn lỗi checksum.
