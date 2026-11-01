import time
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.parking import ParkingSlot, RFIDCard, ParkingSession, SystemAlert
from backend.app.schemas.parking import (
    SlotListResponse, ParkingSlotResponse, SlotOverrideRequest,
    CardTapRequest, GateTapResponse, BarrierStateRequest,
    BarrierSafetySensorRequest, BarrierCommandRequest, CardToggleActiveRequest,
    SensorTelemetryRequest, VisionTelemetryRequest,
    CardResponse, CardCreateRequest, ParkingSessionResponse,
    SystemStatsResponse, AlertResponse,
    SimulatorSlotToggleRequest, SimulatorMismatchRequest
)
from backend.app.services.parking_service import ParkingService
from backend.app.services.websocket_manager import ws_manager
from backend.app.core.hardware_adapter import get_hardware_adapter, set_hardware_mode
from vision.src.camera_stream import get_latest_jpeg_frame


api_router = APIRouter(prefix="/api/v1")

# ==============================================================================
# 1. PARKING SLOTS
# ==============================================================================
@api_router.get("/slots", response_model=SlotListResponse)
def get_parking_slots(db: Session = Depends(get_db)):
    slots = ParkingService.get_all_slots(db)
    total = len(slots)
    available = sum(1 for s in slots if s.status == "EMPTY")
    occupied = sum(1 for s in slots if s.status == "OCCUPIED")
    mismatch = sum(1 for s in slots if s.status == "MISMATCH")
    return SlotListResponse(
        total_slots=total,
        available_slots=available,
        occupied_slots=occupied,
        mismatch_slots=mismatch,
        slots=[ParkingSlotResponse.model_validate(s) for s in slots]
    )

@api_router.post("/slots/{slot_id}/override")
async def override_slot_status(slot_id: str, payload: SlotOverrideRequest, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id.upper()).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    slot.status = payload.status
    if payload.status == "OCCUPIED":
        slot.sensor_occupied = True
        slot.camera_occupied = True
        slot.sensor_distance_cm = 18.0
    elif payload.status == "EMPTY":
        slot.sensor_occupied = False
        slot.camera_occupied = False
        slot.sensor_distance_cm = 120.0
    slot.has_mismatch = (payload.status == "MISMATCH")
    db.commit()

    await ws_manager.broadcast({
        "event_type": "SLOT_UPDATE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "slot_id": slot.slot_id,
            "status": slot.status,
            "sensor_occupied": slot.sensor_occupied,
            "camera_occupied": slot.camera_occupied,
            "has_mismatch": slot.has_mismatch
        }
    })
    return {"message": f"Slot {slot_id} updated to {payload.status}", "slot": ParkingSlotResponse.model_validate(slot)}

# ==============================================================================
# 2. GATE & RFID ACCESS CONTROL
# ==============================================================================
@api_router.post("/gate/entry-tap", response_model=GateTapResponse)
async def gate_entry_tap(payload: CardTapRequest, db: Session = Depends(get_db)):
    return await ParkingService.process_entry_tap(db, payload)

@api_router.post("/gate/exit-tap", response_model=GateTapResponse)
async def gate_exit_tap(payload: CardTapRequest, db: Session = Depends(get_db)):
    return await ParkingService.process_exit_tap(db, payload)

@api_router.post("/gate/barrier-state")
async def update_barrier_state(payload: BarrierStateRequest):
    await ParkingService.set_barrier_state(payload.gate_id, payload.state, payload.angle)
    return {"status": "SUCCESS", "gate_id": payload.gate_id, "state": payload.state, "angle": payload.angle}

@api_router.post("/gate/safety-sensor")
async def update_safety_sensor(payload: BarrierSafetySensorRequest, db: Session = Depends(get_db)):
    """Cập nhật trạng thái cảm biến quang an toàn tại cổng (vật cản chặn cánh barie)."""
    await ParkingService.update_safety_sensor(db, payload.gate_id, payload.has_obstruction)
    return {"status": "SUCCESS", "gate_id": payload.gate_id, "has_obstruction": payload.has_obstruction}

@api_router.post("/gate/command")
async def execute_barrier_command(payload: BarrierCommandRequest, db: Session = Depends(get_db)):
    """Ra lệnh mở hoặc đóng barrier (có kiểm tra khóa liên động an toàn)."""
    success, message = await ParkingService.command_barrier(db, payload.gate_id, payload.command)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "SUCCESS", "gate_id": payload.gate_id, "command": payload.command, "message": message}

# ==============================================================================
# 3. TELEMETRY & VISION INGESTION & LIVE STREAM
# ==============================================================================
@api_router.post("/telemetry/sensors")
async def ingest_sensor_telemetry(payload: SensorTelemetryRequest, db: Session = Depends(get_db)):
    await ParkingService.update_sensor_telemetry(db, payload.readings)
    return {"status": "SUCCESS", "processed_count": len(payload.readings)}

@api_router.post("/vision/occupancy")
@api_router.post("/telemetry/vision")
async def ingest_vision_telemetry(payload: VisionTelemetryRequest, db: Session = Depends(get_db)):
    await ParkingService.update_vision_telemetry(db, payload.slots)
    return {"status": "SUCCESS", "processed_count": len(payload.slots)}

@api_router.get("/vision/frame")
def get_camera_snapshot():
    """Lấy 1 snapshot JPEG của camera giả lập có vẽ bounding boxes ROI."""
    jpeg_bytes = get_latest_jpeg_frame(draw_roi=True)
    if not jpeg_bytes:
        raise HTTPException(status_code=503, detail="Camera stream unavailable")
    return Response(content=jpeg_bytes, media_type="image/jpeg")

@api_router.get("/vision/live-feed")
async def get_live_mjpeg_feed():
    """Luồng video MJPEG truyền phát trực tiếp đến Dashboard."""
    async def frame_generator():
        while True:
            jpeg = get_latest_jpeg_frame(draw_roi=True)
            if jpeg:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            await asyncio.sleep(0.1)  # 10 fps

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ==============================================================================
# 4. CARDS & SESSIONS
# ==============================================================================
@api_router.get("/cards", response_model=list[CardResponse])
def list_cards(db: Session = Depends(get_db)):
    cards = db.query(RFIDCard).all()
    return [CardResponse.model_validate(c) for c in cards]

@api_router.post("/cards/toggle-active", response_model=CardResponse)
def toggle_card_active(payload: CardToggleActiveRequest, db: Session = Depends(get_db)):
    """Khóa hoặc kích hoạt thẻ RFID phục vụ kiểm thử."""
    card = db.query(RFIDCard).filter(RFIDCard.card_uid == payload.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_active = payload.is_active
    db.commit()
    db.refresh(card)
    return CardResponse.model_validate(card)


@api_router.post("/cards", response_model=CardResponse)
def register_card(payload: CardCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(RFIDCard).filter(RFIDCard.card_uid == payload.card_uid).first()
    if existing:
        raise HTTPException(status_code=400, detail="Card UID already registered")
    new_card = RFIDCard(
        card_uid=payload.card_uid,
        owner_name=payload.owner_name,
        vehicle_plate=payload.vehicle_plate,
        card_type=payload.card_type or "STANDARD"
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return CardResponse.model_validate(new_card)

@api_router.get("/sessions/active", response_model=list[ParkingSessionResponse])
def get_active_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ParkingSession).filter(ParkingSession.status == "ACTIVE").order_by(ParkingSession.entry_time.desc()).all()
    return [ParkingSessionResponse.model_validate(s) for s in sessions]

@api_router.get("/sessions/history", response_model=list[ParkingSessionResponse])
def get_session_history(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    sessions = db.query(ParkingSession).order_by(ParkingSession.entry_time.desc()).limit(limit).all()
    return [ParkingSessionResponse.model_validate(s) for s in sessions]

# ==============================================================================
# 5. SYSTEM STATS & ALERTS
# ==============================================================================
@api_router.get("/system/stats", response_model=SystemStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    stats = ParkingService.get_system_stats(db)
    return SystemStatsResponse(**stats)

@api_router.get("/system/alerts", response_model=list[AlertResponse])
@api_router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(limit: int = 20, db: Session = Depends(get_db)):
    alerts = db.query(SystemAlert).order_by(SystemAlert.created_at.desc()).limit(limit).all()
    return [AlertResponse.model_validate(a) for a in alerts]

# ==============================================================================
# 6. SIMULATOR CONTROLS
# ==============================================================================
@api_router.post("/simulator/slot-toggle")
async def simulator_toggle_slot(payload: SimulatorSlotToggleRequest, db: Session = Depends(get_db)):
    if get_hardware_adapter().get_mode() != "SIMULATION":
        raise HTTPException(status_code=403, detail="Simulator endpoints disabled in HARDWARE mode")

    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == payload.slot_id.upper()).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    slot.sensor_occupied = payload.occupied
    slot.camera_occupied = payload.occupied
    slot.sensor_distance_cm = 18.0 if payload.occupied else 125.0
    slot.has_mismatch = False
    slot.status = "OCCUPIED" if payload.occupied else "EMPTY"
    slot.updated_at = datetime.now(timezone.utc)
    db.commit()

    await ws_manager.broadcast({
        "event_type": "SLOT_UPDATE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "slot_id": slot.slot_id,
            "status": slot.status,
            "sensor_occupied": slot.sensor_occupied,
            "camera_occupied": slot.camera_occupied,
            "has_mismatch": slot.has_mismatch
        }
    })
    return {"message": f"Simulator updated {slot.slot_id} to {'OCCUPIED' if payload.occupied else 'EMPTY'}"}

@api_router.post("/simulator/inject-mismatch")
async def simulator_inject_mismatch(payload: SimulatorMismatchRequest, db: Session = Depends(get_db)):
    if get_hardware_adapter().get_mode() != "SIMULATION":
        raise HTTPException(status_code=403, detail="Simulator endpoints disabled in HARDWARE mode")

    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == payload.slot_id.upper()).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    slot.sensor_occupied = payload.sensor_occupied
    slot.camera_occupied = payload.camera_occupied
    slot.sensor_distance_cm = 18.0 if payload.sensor_occupied else 125.0
    slot.has_mismatch = (payload.sensor_occupied != payload.camera_occupied)
    slot.status = "MISMATCH" if slot.has_mismatch else ("OCCUPIED" if payload.sensor_occupied else "EMPTY")
    slot.updated_at = datetime.now(timezone.utc)

    if slot.has_mismatch:
        existing_alert = db.query(SystemAlert).filter(
            SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
            SystemAlert.slot_id == slot.slot_id,
            SystemAlert.is_resolved == False
        ).first()
        if not existing_alert:
            alert = SystemAlert(
                alert_type="SENSOR_CAMERA_MISMATCH",
                slot_id=slot.slot_id,
                severity="WARNING",
                message=f"[Mô phỏng] Sai lệch trạng thái tại {slot.slot_id}: Cảm biến={payload.sensor_occupied}, Camera={payload.camera_occupied}"
            )
            db.add(alert)
    else:
        existing_alert = db.query(SystemAlert).filter(
            SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
            SystemAlert.slot_id == slot.slot_id,
            SystemAlert.is_resolved == False
        ).first()
        if existing_alert:
            existing_alert.is_resolved = True

    db.commit()

    await ws_manager.broadcast({
        "event_type": "MISMATCH_ALERT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "slot_id": slot.slot_id,
            "status": slot.status,
            "sensor_occupied": slot.sensor_occupied,
            "camera_occupied": slot.camera_occupied,
            "has_mismatch": slot.has_mismatch
        }
    })
    return {"message": f"Injected mismatch on {slot.slot_id}", "status": slot.status}

@api_router.post("/simulator/reset")
async def simulator_reset(db: Session = Depends(get_db)):
    if get_hardware_adapter().get_mode() != "SIMULATION":
        raise HTTPException(status_code=403, detail="Simulator endpoints disabled in HARDWARE mode")

    # 1. Reset 4 slots to EMPTY
    slots = db.query(ParkingSlot).all()
    for s in slots:
        s.status = "EMPTY"
        s.sensor_distance_cm = 120.0
        s.sensor_occupied = False
        s.camera_occupied = False
        s.has_mismatch = False

    # 2. Complete all active sessions for clean simulator restart
    active_sessions = db.query(ParkingSession).filter(ParkingSession.status == "ACTIVE").all()
    for sess in active_sessions:
        sess.status = "COMPLETED"
        sess.exit_time = datetime.now(timezone.utc)

    # 3. Ensure all RFID cards are active
    cards = db.query(RFIDCard).all()
    for c in cards:
        c.is_active = True

    adapter = get_hardware_adapter()
    adapter.set_safety_sensor("ENTRY", False)
    adapter.set_safety_sensor("EXIT", False)
    adapter.command_barrier("ENTRY", "CLOSE")
    adapter.command_barrier("EXIT", "CLOSE")

    db.commit()

    await ws_manager.broadcast({
        "event_type": "SYSTEM_RESET",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "All slots reset to EMPTY, active sessions cleared, barriers CLOSED"}
    })
    return {"message": "System reset completed"}

# ==============================================================================
# 7. SYSTEM MODE (SIMULATION VS HARDWARE)
# ==============================================================================
@api_router.get("/system/mode")
def get_system_mode():
    adapter = get_hardware_adapter()
    return {"mode": adapter.get_mode(), "is_simulation": adapter.get_mode() == "SIMULATION"}

@api_router.post("/system/mode")
def change_system_mode(mode: str = Query(..., description="SIMULATION or HARDWARE")):
    adapter = set_hardware_mode(mode)
    return {"status": "SUCCESS", "mode": adapter.get_mode()}

