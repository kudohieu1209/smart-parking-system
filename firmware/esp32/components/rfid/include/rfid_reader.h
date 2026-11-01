/**
 * @file rfid_reader.h
 * @brief Giao diện đọc thẻ RFID RC522 tại Cổng Vào / Cổng Ra qua SPI.
 */

#ifndef RFID_READER_H
#define RFID_READER_H

#include <esp_err.h>
#include "parking_types.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t rfid_reader_init(void);
esp_err_t rfid_reader_poll(gate_id_t gate, char *out_card_uid, size_t max_len);

#ifdef __cplusplus
}
#endif

#endif // RFID_READER_H
