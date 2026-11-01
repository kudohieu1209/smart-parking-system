idf_component_register(
    SRCS "rfid_reader.c"
    INCLUDE_DIRS "include"
    REQUIRES "parking_core" "driver" "esp_rom"
)
