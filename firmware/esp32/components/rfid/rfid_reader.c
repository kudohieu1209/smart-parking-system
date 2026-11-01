/**
 * @file rfid_reader.c
 * @brief Driver MFRC522 SPI hoàn chỉnh cho ESP32 DevKit (Tương thích Wokwi & Phần cứng thật).
 */

#include <stdio.h>
#include <string.h>
#include <esp_log.h>
#include <driver/spi_master.h>
#include <driver/gpio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "rfid_reader.h"
#include "pin_config.h"

static const char *TAG = "MFRC522_RFID";

// ==============================================================================
// MFRC522 REGISTERS & COMMANDS
// ==============================================================================
#define PCD_IDLE              0x00
#define PCD_TRANSCEIVE        0x0C
#define PCD_RESETPHASE        0x0F

#define PICC_REQIDL           0x26
#define PICC_ANTICOLL         0x93

#define CommandReg            0x01
#define ComIEnReg             0x02
#define DivIEnReg             0x03
#define ComIrqReg             0x04
#define DivIrqReg             0x05
#define ErrorReg              0x06
#define Status2Reg            0x08
#define FIFODataReg           0x09
#define FIFOLevelReg          0x0A
#define ControlReg            0x0C
#define BitFramingReg         0x0D
#define ModeReg               0x11
#define TxControlReg          0x14
#define TxASKReg              0x15
#define TModeReg              0x2A
#define TPrescalerReg         0x2B
#define TReloadRegH           0x2C
#define TReloadRegL           0x2D
#define VersionReg            0x37

static spi_device_handle_t g_spi_entry = NULL;
static spi_device_handle_t g_spi_exit = NULL;

// ==============================================================================
// LOW-LEVEL SPI PROTOCOL
// ==============================================================================

static esp_err_t mfrc522_write_reg(spi_device_handle_t spi, uint8_t reg, uint8_t value) {
    if (!spi) return ESP_ERR_INVALID_STATE;
    uint8_t tx_data[2] = { (uint8_t)((reg << 1) & 0x7E), value };
    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = tx_data,
        .rx_buffer = NULL
    };
    return spi_device_polling_transmit(spi, &t);
}

static uint8_t mfrc522_read_reg(spi_device_handle_t spi, uint8_t reg) {
    if (!spi) return 0;
    uint8_t tx_data[2] = { (uint8_t)(((reg << 1) & 0x7E) | 0x80), 0x00 };
    uint8_t rx_data[2] = { 0 };
    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = tx_data,
        .rx_buffer = rx_data
    };
    if (spi_device_polling_transmit(spi, &t) == ESP_OK) {
        return rx_data[1];
    }
    return 0;
}

static void mfrc522_set_bit_mask(spi_device_handle_t spi, uint8_t reg, uint8_t mask) {
    uint8_t current = mfrc522_read_reg(spi, reg);
    mfrc522_write_reg(spi, reg, current | mask);
}

static void mfrc522_clear_bit_mask(spi_device_handle_t spi, uint8_t reg, uint8_t mask) {
    uint8_t current = mfrc522_read_reg(spi, reg);
    mfrc522_write_reg(spi, reg, current & (~mask));
}

static void mfrc522_antenna_on(spi_device_handle_t spi) {
    uint8_t temp = mfrc522_read_reg(spi, TxControlReg);
    if ((temp & 0x03) != 0x03) {
        mfrc522_set_bit_mask(spi, TxControlReg, 0x03);
    }
}

static esp_err_t mfrc522_reset_chip(spi_device_handle_t spi) {
    mfrc522_write_reg(spi, CommandReg, PCD_RESETPHASE);
    vTaskDelay(pdMS_TO_TICKS(10));

    // Cấu hình Timer & Bộ điều chế RF
    mfrc522_write_reg(spi, TModeReg, 0x8D);
    mfrc522_write_reg(spi, TPrescalerReg, 0x3E);
    mfrc522_write_reg(spi, TReloadRegL, 30);
    mfrc522_write_reg(spi, TReloadRegH, 0);

    mfrc522_write_reg(spi, TxASKReg, 0x40);
    mfrc522_write_reg(spi, ModeReg, 0x3D);

    mfrc522_antenna_on(spi);
    return ESP_OK;
}

static spi_device_handle_t get_gate_handle(gate_id_t gate) {
    return (gate == GATE_ENTRY) ? g_spi_entry : g_spi_exit;
}

// ==============================================================================
// PUBLIC DRIVER API
// ==============================================================================

esp_err_t rfid_reader_init(void) {
    ESP_LOGI(TAG, "Initializing SPI bus for 2x MFRC522 Readers (SCK=%d, MISO=%d, MOSI=%d)...",
             PIN_RFID_SPI_SCK, PIN_RFID_SPI_MISO, PIN_RFID_SPI_MOSI);

    // 1. Cấu hình chân Reset chung
    gpio_reset_pin((gpio_num_t)PIN_RFID_RST);
    gpio_set_direction((gpio_num_t)PIN_RFID_RST, GPIO_MODE_OUTPUT);
    gpio_set_level((gpio_num_t)PIN_RFID_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level((gpio_num_t)PIN_RFID_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(10));

    // 2. Khởi tạo bus SPI (VSPI_HOST)
    spi_bus_config_t buscfg = {
        .miso_io_num = PIN_RFID_SPI_MISO,
        .mosi_io_num = PIN_RFID_SPI_MOSI,
        .sclk_io_num = PIN_RFID_SPI_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 64
    };
    esp_err_t ret = spi_bus_initialize(SPI3_HOST, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to initialize SPI bus: %s", esp_err_to_name(ret));
        return ret;
    }

    // 3. Đăng ký thiết bị MFRC522 Cổng Vào (ENTRY_CS = GPIO 5)
    spi_device_interface_config_t devcfg_entry = {
        .clock_speed_hz = 4000000, // 4 MHz
        .mode = 0,                 // SPI Mode 0
        .spics_io_num = PIN_RFID_ENTRY_CS,
        .queue_size = 3
    };
    ret = spi_bus_add_device(SPI3_HOST, &devcfg_entry, &g_spi_entry);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to attach Entry MFRC522 device: %s", esp_err_to_name(ret));
    }

    // 4. Đăng ký thiết bị MFRC522 Cổng Ra (EXIT_CS = GPIO 4)
    spi_device_interface_config_t devcfg_exit = {
        .clock_speed_hz = 4000000,
        .mode = 0,
        .spics_io_num = PIN_RFID_EXIT_CS,
        .queue_size = 3
    };
    ret = spi_bus_add_device(SPI3_HOST, &devcfg_exit, &g_spi_exit);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to attach Exit MFRC522 device: %s", esp_err_to_name(ret));
    }

    // 5. Khởi tạo chip
    if (g_spi_entry) {
        mfrc522_reset_chip(g_spi_entry);
        uint8_t ver = mfrc522_read_reg(g_spi_entry, VersionReg);
        ESP_LOGI(TAG, "Entry MFRC522 initialized. Chip Version: 0x%02X", ver);
    }
    if (g_spi_exit) {
        mfrc522_reset_chip(g_spi_exit);
        uint8_t ver = mfrc522_read_reg(g_spi_exit, VersionReg);
        ESP_LOGI(TAG, "Exit MFRC522 initialized. Chip Version: 0x%02X", ver);
    }

    return ESP_OK;
}

esp_err_t rfid_reader_get_version(gate_id_t gate, uint8_t *out_version) {
    spi_device_handle_t spi = get_gate_handle(gate);
    if (!spi || !out_version) return ESP_ERR_INVALID_ARG;
    *out_version = mfrc522_read_reg(spi, VersionReg);
    return (*out_version == 0x00 || *out_version == 0xFF) ? ESP_ERR_INVALID_RESPONSE : ESP_OK;
}

static esp_err_t mfrc522_to_card(spi_device_handle_t spi, uint8_t cmd,
                                 const uint8_t *send_data, uint8_t send_len,
                                 uint8_t *back_data, uint32_t *back_len) {
    uint8_t irq_en = 0x77;
    uint8_t wait_irq = 0x30;

    mfrc522_write_reg(spi, ComIEnReg, irq_en | 0x80);
    mfrc522_clear_bit_mask(spi, ComIrqReg, 0x80);
    mfrc522_set_bit_mask(spi, FIFOLevelReg, 0x80); // FlushBuffer

    mfrc522_write_reg(spi, CommandReg, PCD_IDLE);

    // Ghi dữ liệu vào FIFO
    for (int i = 0; i < send_len; i++) {
        mfrc522_write_reg(spi, FIFODataReg, send_data[i]);
    }

    // Thực thi lệnh phát / nhận
    mfrc522_write_reg(spi, CommandReg, cmd);
    if (cmd == PCD_TRANSCEIVE) {
        mfrc522_set_bit_mask(spi, BitFramingReg, 0x80); // StartSend
    }

    // Chờ nhận dữ liệu hoặc timeout (25ms)
    int timeout = 250;
    uint8_t n = 0;
    do {
        ets_delay_us(100);
        n = mfrc522_read_reg(spi, ComIrqReg);
        timeout--;
    } while ((timeout > 0) && !(n & 0x01) && !(n & wait_irq));

    mfrc522_clear_bit_mask(spi, BitFramingReg, 0x80);

    if (timeout <= 0 || (n & 0x01)) {
        return ESP_ERR_TIMEOUT;
    }

    uint8_t error = mfrc522_read_reg(spi, ErrorReg);
    if (error & 0x1B) {
        return ESP_ERR_INVALID_RESPONSE;
    }

    if (back_data && back_len) {
        uint8_t fifo_len = mfrc522_read_reg(spi, FIFOLevelReg);
        if (fifo_len > *back_len) fifo_len = *back_len;
        for (int i = 0; i < fifo_len; i++) {
            back_data[i] = mfrc522_read_reg(spi, FIFODataReg);
        }
        *back_len = fifo_len;
    }

    return ESP_OK;
}

esp_err_t rfid_reader_poll(gate_id_t gate, char *out_card_uid, size_t max_len) {
    if (!out_card_uid || max_len < 16) {
        return ESP_ERR_INVALID_ARG;
    }

    spi_device_handle_t spi = get_gate_handle(gate);
    if (!spi) return ESP_ERR_INVALID_STATE;

    // 1. Kiểm tra Version để phát hiện chip có kết nối không
    uint8_t ver = mfrc522_read_reg(spi, VersionReg);
    if (ver == 0x00 || ver == 0xFF) {
        return ESP_ERR_INVALID_RESPONSE; // Chip chưa kết nối hoặc mất nguồn
    }

    // 2. Yêu cầu tìm thẻ (PICC_REQIDL: 7-bit command)
    mfrc522_write_reg(spi, BitFramingReg, 0x07);
    uint8_t tag_type[2] = {0};
    uint32_t back_len = sizeof(tag_type);
    uint8_t req_cmd = PICC_REQIDL;
    esp_err_t ret = mfrc522_to_card(spi, PCD_TRANSCEIVE, &req_cmd, 1, tag_type, &back_len);
    if (ret != ESP_OK || back_len == 0) {
        return ESP_ERR_NOT_FOUND; // Không có thẻ trong vùng quét
    }

    // 3. Chống xung đột & đọc 4-byte UID (PICC_ANTICOLL)
    mfrc522_write_reg(spi, BitFramingReg, 0x00);
    uint8_t anticoll_cmd[2] = { PICC_ANTICOLL, 0x20 };
    uint8_t uid_buf[5] = {0};
    back_len = sizeof(uid_buf);
    ret = mfrc522_to_card(spi, PCD_TRANSCEIVE, anticoll_cmd, 2, uid_buf, &back_len);
    if (ret != ESP_OK || back_len < 4) {
        return ESP_ERR_INVALID_RESPONSE;
    }

    // 4. Kiểm tra checksum BCC (XOR 4 byte đầu phải bằng byte thứ 5)
    uint8_t bcc_check = uid_buf[0] ^ uid_buf[1] ^ uid_buf[2] ^ uid_buf[3];
    if (back_len >= 5 && bcc_check != uid_buf[4]) {
        ESP_LOGW(TAG, "MFRC522 Checksum mismatch: calculated 0x%02X, received 0x%02X", bcc_check, uid_buf[4]);
        return ESP_ERR_INVALID_CRC;
    }

    // 5. Định dạng mã UID chuẩn cho hệ thống
    snprintf(out_card_uid, max_len, "%02X:%02X:%02X:%02X",
             uid_buf[0], uid_buf[1], uid_buf[2], uid_buf[3]);

    return ESP_OK;
}
