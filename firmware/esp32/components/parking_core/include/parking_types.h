/**
 * @file parking_types.h
 * @brief Định nghĩa các kiểu dữ liệu dùng chung trong toàn bộ firmware ESP32.
 */

#ifndef PARKING_TYPES_H
#define PARKING_TYPES_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_SLOTS 4

typedef enum {
    SLOT_EMPTY = 0,
    SLOT_OCCUPIED,
    SLOT_UNKNOWN,
    SLOT_FAULT
} slot_state_t;

typedef enum {
    GATE_ENTRY = 0,
    GATE_EXIT
} gate_id_t;

typedef enum {
    BARRIER_CLOSED = 0,
    BARRIER_OPEN
} barrier_state_t;

typedef struct {
    char slot_id[8];            // "P01", "P02", ...
    float distance_cm;          // Khoảng cách đo được
    bool occupied;              // Có xe hay không
    uint32_t last_update_ms;    // Timestamp tick
} slot_telemetry_t;

typedef struct {
    gate_id_t gate_id;
    char card_uid[32];          // Mã UID thẻ (VD: "TAG-8F2B10")
    uint32_t tap_time_ms;
} rfid_event_t;

#ifdef __cplusplus
}
#endif

#endif // PARKING_TYPES_H
