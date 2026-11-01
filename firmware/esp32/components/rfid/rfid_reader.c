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
#include <esp_rom_sys.h>

#include "rfid_reader.h"
#include "pin_config.h"

static const char *TAG = "MFRC522_RFID";

#ifndef CONFIG_SMART_PARKING_RFID_DEBUG
#define CONFIG_SMART_PARKING_RFID_DEBUG 1
#endif

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

/**
 * @brief Ghi chuỗi byte liên tục vào FIFODataReg trong một SPI transaction duy nhất.
 */
static esp_err_t mfrc522_write_fifo(spi_device_handle_t spi, const uint8_t *data, size_t len) {
    if (!spi || !data || len == 0 || len > 64) return ESP_ERR_INVALID_ARG;
    uint8_t tx_buf[65];
    tx_buf[0] = (uint8_t)((FIFODataReg << 1) & 0x7E); // MSB = 0 cho lệnh ghi
    memcpy(&tx_buf[1], data, len);

    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = tx_buf,
        .rx_buffer = NULL
    };
    return spi_device_polling_transmit(spi, &t);
}

/**
 * @brief Đọc chuỗi byte liên tục từ FIFODataReg theo đúng chuẩn streaming SPI của MFRC522.
 * Giữ CS LOW trong toàn bộ quá trình đọc để tránh pop đúp/bỏ sót byte trong FIFO.
 */
static esp_err_t mfrc522_read_fifo(spi_device_handle_t spi, uint8_t *data, size_t len) {
    if (!spi || !data || len == 0 || len > 64) return ESP_ERR_INVALID_ARG;
    uint8_t tx_buf[65] = {0};
    uint8_t rx_buf[65] = {0};

    uint8_t addr = (uint8_t)(((FIFODataReg << 1) & 0x7E) | 0x80); // MSB = 1 cho lệnh đọc
    tx_buf[0] = addr;
    for (size_t i = 1; i < len; i++) {
        tx_buf[i] = addr; // Gửi địa chỉ để clock out các byte tiếp theo
    }
    tx_buf[len] = 0x00; // Byte cuối cùng gửi 0x00 để kết thúc luồng đọc

    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = tx_buf,
        .rx_buffer = rx_buf
    };
    esp_err_t ret = spi_device_polling_transmit(spi, &t);
    if (ret != ESP_OK) return ret;

    // rx_buf[0] là phản hồi giả khi gửi địa chỉ, dữ liệu thực nằm từ rx_buf[1] đến rx_buf[len]
    for (size_t i = 0; i < len; i++) {
        data[i] = rx_buf[i + 1];
    }
    return ESP_OK;
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

    // 2. Khởi tạo bus SPI (SPI3_HOST / VSPI)
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

/**
 * @brief Giao tiếp cấp thấp với thẻ RFID (PICC) qua lệnh phát/nhận PCD_TRANSCEIVE.
 * Triển khai chuẩn ISO 14443-3 / MFRC522: hủy lệnh đang chạy, xóa triệt để IRQ, flush FIFO.
 */
static esp_err_t mfrc522_to_card(spi_device_handle_t spi, uint8_t cmd,
                                 const uint8_t *send_data, uint8_t send_len,
                                 uint8_t *back_data, uint32_t *back_len,
                                 uint8_t *valid_bits) {
    uint8_t irq_en = 0x77;
    uint8_t wait_irq = 0x30; // Chờ RxIRq (0x20) hoặc IdleIRq (0x10)

    // 1. Dừng bất kỳ lệnh nào đang thực thi trên chip
    mfrc522_write_reg(spi, CommandReg, PCD_IDLE);

    // 2. Xóa toàn bộ 7 cờ ngắt trong ComIrqReg (Ghi 1 vào các bit khi bit 7 Set1 = 0 sẽ xóa cờ)
    mfrc522_write_reg(spi, ComIrqReg, 0x7F);

    // 3. Khởi tạo/Flush FIFO buffer
    mfrc522_set_bit_mask(spi, FIFOLevelReg, 0x80);

    // 4. Bật ngắt giao tiếp
    mfrc522_write_reg(spi, ComIEnReg, irq_en | 0x80);

    // 5. Nạp dữ liệu phát vào FIFO theo chuẩn multi-byte
    if (send_data && send_len > 0) {
        mfrc522_write_fifo(spi, send_data, send_len);
    }

    // 6. Thực thi lệnh phát / nhận
    mfrc522_write_reg(spi, CommandReg, cmd);
    if (cmd == PCD_TRANSCEIVE) {
        mfrc522_set_bit_mask(spi, BitFramingReg, 0x80); // StartSend = 1
    }

    // 7. Chờ nhận dữ liệu hoặc timeout (25ms)
    int timeout = 250;
    uint8_t irq_val = 0;
    do {
        esp_rom_delay_us(100);
        irq_val = mfrc522_read_reg(spi, ComIrqReg);
        timeout--;
    } while ((timeout > 0) && !(irq_val & 0x01) && !(irq_val & wait_irq));

    // 8. Tắt cờ StartSend
    mfrc522_clear_bit_mask(spi, BitFramingReg, 0x80);

    // 9. Kiểm tra lỗi timeout hoặc timer IRQ
    if (timeout <= 0 || (irq_val & 0x01)) {
        return ESP_ERR_TIMEOUT;
    }

    // 10. Kiểm tra thanh ghi lỗi ErrorReg
    uint8_t error_val = mfrc522_read_reg(spi, ErrorReg);
    if (error_val & 0x1B) { // BufferOvfl (0x10), ParityErr (0x02), ProtocolErr (0x01), CollErr (0x08)
        return ESP_ERR_INVALID_RESPONSE;
    }

    // 11. Đọc dữ liệu phản hồi từ FIFO
    if (back_data && back_len) {
        uint8_t fifo_len = mfrc522_read_reg(spi, FIFOLevelReg) & 0x7F;
        uint8_t rx_last_bits = mfrc522_read_reg(spi, ControlReg) & 0x07;

        if (valid_bits) {
            *valid_bits = rx_last_bits;
        }

        if (fifo_len > *back_len) {
            fifo_len = (uint8_t)(*back_len);
        }

        if (fifo_len > 0) {
            esp_err_t r_err = mfrc522_read_fifo(spi, back_data, fifo_len);
            if (r_err != ESP_OK) return r_err;
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
    uint8_t valid_bits = 0;
    esp_err_t ret = mfrc522_to_card(spi, PCD_TRANSCEIVE, &req_cmd, 1, tag_type, &back_len, &valid_bits);
    if (ret != ESP_OK || back_len == 0) {
        return ESP_ERR_NOT_FOUND; // Không có thẻ trong vùng quét
    }

    // Inter-frame Delay: Đảm bảo thẻ ổn định sang READY state sau ATQA (theo chuẩn ISO 14443-3)
    esp_rom_delay_us(1000);

    // 3. Chống xung đột & đọc 4-byte UID (PICC_ANTICOLL, Cascade Level 1)
    mfrc522_write_reg(spi, BitFramingReg, 0x00); // 8-bit frames, RxAlign = 0
    uint8_t anticoll_cmd[2] = { PICC_ANTICOLL, 0x20 };
    uint8_t uid_buf[5] = {0};
    back_len = sizeof(uid_buf);
    valid_bits = 0;

    ret = mfrc522_to_card(spi, PCD_TRANSCEIVE, anticoll_cmd, 2, uid_buf, &back_len, &valid_bits);
    if (ret != ESP_OK) {
        return ESP_ERR_INVALID_RESPONSE;
    }

    uint8_t bcc_calc = uid_buf[0] ^ uid_buf[1] ^ uid_buf[2] ^ uid_buf[3];
    uint8_t bcc_recv = uid_buf[4];
    uint8_t err_reg = mfrc522_read_reg(spi, ErrorReg);
    uint8_t irq_reg = mfrc522_read_reg(spi, ComIrqReg);

#if CONFIG_SMART_PARKING_RFID_DEBUG
    ESP_LOGI(TAG, "[%s RFID] Raw UID: %02X %02X %02X %02X %02X | FIFO_len=%lu, RxLastBits=%d, ErrorReg=0x%02X, ComIrq=0x%02X | BCC calc=0x%02X, recv=0x%02X",
             (gate == GATE_ENTRY) ? "ENTRY" : "EXIT",
             uid_buf[0], uid_buf[1], uid_buf[2], uid_buf[3], uid_buf[4],
             (unsigned long)back_len, (int)valid_bits, err_reg, irq_reg,
             bcc_calc, bcc_recv);
#endif

    // 4. Với thẻ 4-byte UID, phản hồi bắt buộc phải đủ 5 bytes và valid_bits = 0
    if (back_len != 5 || valid_bits != 0) {
        ESP_LOGW(TAG, "[%s RFID] Invalid response framing: len=%lu, validBits=%d",
                 (gate == GATE_ENTRY) ? "ENTRY" : "EXIT", (unsigned long)back_len, (int)valid_bits);
        return ESP_ERR_INVALID_RESPONSE;
    }

    // 5. Kiểm tra checksum BCC (XOR 4 byte đầu phải bằng byte thứ 5)
    if (bcc_calc != bcc_recv) {
        ESP_LOGW(TAG, "[%s RFID] MFRC522 Checksum mismatch: calculated 0x%02X, received 0x%02X",
                 (gate == GATE_ENTRY) ? "ENTRY" : "EXIT", bcc_calc, bcc_recv);
        return ESP_ERR_INVALID_CRC;
    }

    // 6. Định dạng mã UID chuẩn cho hệ thống (VD: "30:A1:23:45")
    snprintf(out_card_uid, max_len, "%02X:%02X:%02X:%02X",
             uid_buf[0], uid_buf[1], uid_buf[2], uid_buf[3]);

    return ESP_OK;
}
