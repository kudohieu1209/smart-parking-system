/**
 * @file barrier_controller.c
 * @brief Điều khiển Servo Barrier bằng phần cứng LEDC PWM và cảm biến quang an toàn.
 */

#include <stdio.h>
#include <esp_log.h>
#include <driver/gpio.h>
#include <driver/ledc.h>
#include "barrier_controller.h"
#include "pin_config.h"

static const char *TAG = "BARRIER_LEDC";

// 50Hz PWM = chu kỳ 20ms = 20,000 µs
// 13-bit độ phân giải = 8192 ticks (1 tick ~ 2.4414 µs)
// 0 độ (Đóng): 500 µs  -> (500 * 8192) / 20000 = 205 ticks
// 90 độ (Mở): 1500 µs -> (1500 * 8192) / 20000 = 614 ticks
#define SERVO_DUTY_CLOSED_0_DEG    205
#define SERVO_DUTY_OPEN_90_DEG     614

static barrier_state_t g_barrier_states[2] = { BARRIER_CLOSED, BARRIER_CLOSED };
static int g_barrier_angles[2] = { 0, 0 };

static ledc_channel_t get_gate_channel(gate_id_t gate) {
    return (gate == GATE_ENTRY) ? LEDC_CHANNEL_0 : LEDC_CHANNEL_1;
}

esp_err_t barrier_controller_init(void) {
    ESP_LOGI(TAG, "Initializing Barrier Controller (Entry PWM: GPIO %d, Exit PWM: GPIO %d)...",
             PIN_SERVO_BARRIER_ENTRY, PIN_SERVO_BARRIER_EXIT);

    // 1. Cấu hình LEDC Timer (50 Hz, 13-bit)
    ledc_timer_config_t timer_conf = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_13_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = 50,
        .clk_cfg = LEDC_AUTO_CLK
    };
    esp_err_t ret = ledc_timer_config(&timer_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure LEDC timer: %s", esp_err_to_name(ret));
        return ret;
    }

    // 2. Cấu hình Channel cho Cổng Vào (GPIO 13)
    ledc_channel_config_t ch_entry = {
        .gpio_num = PIN_SERVO_BARRIER_ENTRY,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_0,
        .duty = SERVO_DUTY_CLOSED_0_DEG,
        .hpoint = 0
    };
    ledc_channel_config(&ch_entry);

    // 3. Cấu hình Channel cho Cổng Ra (GPIO 14)
    ledc_channel_config_t ch_exit = {
        .gpio_num = PIN_SERVO_BARRIER_EXIT,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_1,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_0,
        .duty = SERVO_DUTY_CLOSED_0_DEG,
        .hpoint = 0
    };
    ledc_channel_config(&ch_exit);

    // 4. Cấu hình chân Cảm biến an toàn quang (PULL-UP, Active LOW)
    gpio_reset_pin((gpio_num_t)PIN_SAFETY_IR_ENTRY);
    gpio_set_direction((gpio_num_t)PIN_SAFETY_IR_ENTRY, GPIO_MODE_INPUT);
    gpio_pullup_en((gpio_num_t)PIN_SAFETY_IR_ENTRY);

    gpio_reset_pin((gpio_num_t)PIN_SAFETY_IR_EXIT);
    gpio_set_direction((gpio_num_t)PIN_SAFETY_IR_EXIT, GPIO_MODE_INPUT);
    gpio_pullup_en((gpio_num_t)PIN_SAFETY_IR_EXIT);

    g_barrier_states[GATE_ENTRY] = BARRIER_CLOSED;
    g_barrier_states[GATE_EXIT] = BARRIER_CLOSED;
    g_barrier_angles[GATE_ENTRY] = 0;
    g_barrier_angles[GATE_EXIT] = 0;

    ESP_LOGI(TAG, "Barrier LEDC PWM and Safety IR pins initialized successfully. Default: 0° CLOSED.");
    return ESP_OK;
}

bool barrier_is_obstruction_detected(gate_id_t gate) {
    gpio_num_t pin = (gate == GATE_ENTRY) ? (gpio_num_t)PIN_SAFETY_IR_ENTRY : (gpio_num_t)PIN_SAFETY_IR_EXIT;
    // Cảm biến quang tích cực mức thấp (LOW = có vật cản che chùm tia)
    return (gpio_get_level(pin) == 0);
}

esp_err_t barrier_open(gate_id_t gate) {
    ledc_channel_t ch = get_gate_channel(gate);
    ESP_LOGI(TAG, "Gate %s: Setting servo to 90° OPEN.", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");

    ledc_set_duty(LEDC_LOW_SPEED_MODE, ch, SERVO_DUTY_OPEN_90_DEG);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ch);

    g_barrier_states[gate] = BARRIER_OPEN;
    g_barrier_angles[gate] = 90;
    return ESP_OK;
}

esp_err_t barrier_close(gate_id_t gate) {
    // KHÓA LIÊN ĐỘNG AN TOÀN: Tuyệt đối không đóng nếu có vật cản
    if (barrier_is_obstruction_detected(gate)) {
        ESP_LOGW(TAG, "Gate %s: Obstruction detected! SAFETY INTERLOCK PREVENTS BARRIER CLOSING.",
                 (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");
        return ESP_ERR_INVALID_STATE;
    }

    ledc_channel_t ch = get_gate_channel(gate);
    ESP_LOGI(TAG, "Gate %s: Path is clear. Setting servo to 0° CLOSED.", (gate == GATE_ENTRY) ? "ENTRY" : "EXIT");

    ledc_set_duty(LEDC_LOW_SPEED_MODE, ch, SERVO_DUTY_CLOSED_0_DEG);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ch);

    g_barrier_states[gate] = BARRIER_CLOSED;
    g_barrier_angles[gate] = 0;
    return ESP_OK;
}

barrier_state_t barrier_get_state(gate_id_t gate) {
    return g_barrier_states[gate];
}

int barrier_get_angle(gate_id_t gate) {
    return g_barrier_angles[gate];
}
