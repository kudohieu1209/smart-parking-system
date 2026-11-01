#include <stdio.h>
#include <esp_log.h>
#include <driver/gpio.h>
#include <driver/ledc.h>
#include "barrier_controller.h"
#include "pin_config.h"

static const char *TAG = "BARRIER_CTRL";

static barrier_state_t g_barrier_states[2] = { BARRIER_CLOSED, BARRIER_CLOSED };

esp_err_t barrier_controller_init(void) {
    ESP_LOGI(TAG, "Initializing barrier servo controller (Entry Pin: %d, Exit Pin: %d)...",
             PIN_SERVO_BARRIER_ENTRY, PIN_SERVO_BARRIER_EXIT);

    // Cấu hình chân cảm biến an toàn quang (PULL-UP)
    gpio_reset_pin(PIN_SAFETY_IR_ENTRY);
    gpio_set_direction(PIN_SAFETY_IR_ENTRY, GPIO_MODE_INPUT);
    gpio_pullup_en(PIN_SAFETY_IR_ENTRY);

    gpio_reset_pin(PIN_SAFETY_IR_EXIT);
    gpio_set_direction(PIN_SAFETY_IR_EXIT, GPIO_MODE_INPUT);
    gpio_pullup_en(PIN_SAFETY_IR_EXIT);

    ESP_LOGI(TAG, "Barrier controller initialized. Default state: CLOSED.");
    return ESP_OK;
}

bool barrier_is_obstruction_detected(gate_id_t gate) {
    gpio_num_t pin = (gate == GATE_ENTRY) ? PIN_SAFETY_IR_ENTRY : PIN_SAFETY_IR_EXIT;
    // Cảm biến quang tích cực mức thấp (LOW = có vật cản)
    return (gpio_get_level(pin) == 0);
}

esp_err_t barrier_open(gate_id_t gate) {
    ESP_LOGI(TAG, "Gate %s: Opening barrier to 90 degrees.", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
    g_barrier_states[gate] = BARRIER_OPEN;
    return ESP_OK;
}

esp_err_t barrier_close(gate_id_t gate) {
    // Kiểm tra an toàn trước khi hạ barrier
    if (barrier_is_obstruction_detected(gate)) {
        ESP_LOGW(TAG, "Gate %s: Obstruction detected! CANNOT CLOSE BARRIER.", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
        return ESP_ERR_INVALID_STATE;
    }

    ESP_LOGI(TAG, "Gate %s: Closing barrier to 0 degrees.", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
    g_barrier_states[gate] = BARRIER_CLOSED;
    return ESP_OK;
}

barrier_state_t barrier_get_state(gate_id_t gate) {
    return g_barrier_states[gate];
}
