idf_component_register(
    SRCS "ultrasonic_sensor.c"
    INCLUDE_DIRS "include"
    REQUIRES "parking_core" "driver" "esp_rom" "esp_timer"
)
