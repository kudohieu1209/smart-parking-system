idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES "freertos" "parking_core" "sensor" "rfid" "barrier" "network" "display"
)
