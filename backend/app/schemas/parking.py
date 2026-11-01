import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# --- Parking Slots ---
class ParkingSlotBase(BaseModel):
    slot_id: str
    status: str
    sensor_distance_cm: float
    sensor_occupied: bool
    camera_occupied: bool
    camera_confidence: float
    has_mismatch: bool
    updated_at: Optional[datetime.datetime] = None

class ParkingSlotResponse(ParkingSlotBase):
    model_config = ConfigDict(from_attributes=True)

class SlotListResponse(BaseModel):
    total_slots: int
    available_slots: int
    occupied_slots: int
    mismatch_slots: int
    slots: List[ParkingSlotResponse]

class SlotOverrideRequest(BaseModel):
    status: str = Field(..., description="EMPTY, OCCUPIED, MISMATCH, DISABLED")
    reason: Optional[str] = "MANUAL_OVERRIDE"

# --- Gate & RFID ---
class CardTapRequest(BaseModel):
    card_uid: str
    gate_id: str = Field("ENTRY", description="ENTRY or EXIT")

class CardResponse(BaseModel):
    card_uid: str
    owner_name: str
    vehicle_plate: str
    card_type: str
    is_active: bool
    created_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CardCreateRequest(BaseModel):
    card_uid: str
    owner_name: str
    vehicle_plate: str
    card_type: Optional[str] = "STANDARD"

class ParkingSessionResponse(BaseModel):
    id: int
    card_uid: str
    vehicle_plate: Optional[str] = None
    slot_id: Optional[str] = None
    entry_time: datetime.datetime
    exit_time: Optional[datetime.datetime] = None
    duration_minutes: int
    fee_amount: int
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class GateTapResponse(BaseModel):
    status: str  # ALLOWED or REJECTED
    action: str  # OPEN_BARRIER or KEEP_CLOSED
    gate_id: str
    message: str
    session: Optional[ParkingSessionResponse] = None
    reason: Optional[str] = None

class BarrierStateRequest(BaseModel):
    gate_id: str = "ENTRY"
    state: str = Field("CLOSED", description="OPEN or CLOSED")
    angle: int = 0

class BarrierSafetySensorRequest(BaseModel):
    gate_id: str = Field("ENTRY", description="ENTRY or EXIT")
    has_obstruction: bool = Field(False, description="True if obstacle detected in barrier line")

class BarrierCommandRequest(BaseModel):
    gate_id: str = Field("ENTRY", description="ENTRY or EXIT")
    command: str = Field(..., description="OPEN or CLOSE")

class CardToggleActiveRequest(BaseModel):
    card_uid: str
    is_active: bool


# --- Telemetry & Vision ---
class SensorReading(BaseModel):
    slot_id: str
    distance_cm: float
    occupied: bool

class SensorTelemetryRequest(BaseModel):
    device_id: str = "ESP32_CORE_01"
    readings: List[SensorReading]

class VisionSlotReading(BaseModel):
    slot_id: str
    state: str  # EMPTY or OCCUPIED
    confidence: float = 1.0

class VisionTelemetryRequest(BaseModel):
    camera_id: str = "CAM_MAIN_01"
    slots: List[VisionSlotReading]

# --- Simulator ---
class SimulatorSlotToggleRequest(BaseModel):
    slot_id: str
    occupied: bool

class SimulatorMismatchRequest(BaseModel):
    slot_id: str
    sensor_occupied: bool
    camera_occupied: bool

# --- System & Alerts ---
class AlertResponse(BaseModel):
    id: int
    alert_type: str
    slot_id: Optional[str] = None
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class SystemStatsResponse(BaseModel):
    total_slots: int
    available_slots: int
    occupied_slots: int
    mismatch_slots: int
    active_sessions_count: int
    total_revenue_vnd: int
    barrier_entry_state: str
    barrier_exit_state: str
    barrier_entry_angle: int = 0
    barrier_exit_angle: int = 0
    barrier_entry_obstruction: bool = False
    barrier_exit_obstruction: bool = False
    is_simulation_mode: bool = True
    system_mode: str = "SIMULATION"
    esp32_online: bool = True
    camera_online: bool = True


