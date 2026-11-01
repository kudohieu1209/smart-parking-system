/**
 * @file rfid_reader.h
 * @brief Driver đầu đọc thẻ RFID MFRC522 chuẩn SPI cho ESP32 & Wokwi.
 * 
 * Hỗ trợ 2 đầu đọc MFRC522 độc lập (Cổng Vào & Cổng Ra) trên cùng bus SPI.
 */

#ifndef RFID_READER_H
#define RFID_READER_H

#include <esp_err.h>
#include <stddef.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Khởi tạo SPI bus và cấu hình 2 chip MFRC522 (ENTRY_CS & EXIT_CS).
 */
esp_err_t rfid_reader_init(void);

/**
 * @brief Quét thẻ tại một cổng nhất định (ENTRY hoặc EXIT).
 * 
 * @param gate Cổng cần quét (GATE_ENTRY hoặc GATE_EXIT)
 * @param out_card_uid Chuỗi chứa mã UID (VD: "30A12345" hoặc "01:02:03:04")
 * @param max_len Độ dài tối đa của buffer (tối thiểu 16 bytes)
 * @return esp_err_t:
 *         - ESP_OK: Đã phát hiện thẻ và đọc thành công UID
 *         - ESP_ERR_NOT_FOUND: Không có thẻ trong từ trường anten
 *         - ESP_ERR_INVALID_RESPONSE: Lỗi giao tiếp SPI / sai checksum BCC
 */
esp_err_t rfid_reader_poll(gate_id_t gate, char *out_card_uid, size_t max_len);

/**
 * @brief Kiểm tra phiên bản firmware của chip MFRC522 qua thanh ghi VersionReg.
 * 
 * @param gate Cổng cần kiểm tra
 * @param out_version Trả về mã phiên bản (thường là 0x91 hoặc 0x92)
 * @return esp_err_t ESP_OK nếu chip phản hồi
 */
esp_err_t rfid_reader_get_version(gate_id_t gate, uint8_t *out_version);

#ifdef __cplusplus
}
#endif

#endif // RFID_READER_H
