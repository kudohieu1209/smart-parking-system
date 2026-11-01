import math
import asyncio
from datetime import datetime, timezone
from typing import Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.parking import ParkingSlot, RFIDCard, ParkingSession, SystemAlert
from backend.app.schemas.parking import (
    CardTapRequest, GateTapResponse, ParkingSessionResponse,
    SensorReading, VisionSlotReading
)
from backend.app.services.websocket_manager import ws_manager
from backend.app.core.config import settings
from backend.app.core.hardware_adapter import get_hardware_adapter

logger = logging.getLogger("parking_service")


class ParkingService:
    _entry_lock = asyncio.Lock()
    last_sensor_telemetry_time: Optional[datetime] = None
    last_vision_telemetry_time: Optional[datetime] = None

    @staticmethod
    def seed_initial_data(db: Session):
        """Khởi tạo 4 ô đỗ và danh sách thẻ demo nếu cơ sở dữ liệu trống."""
        # 1. 4 vị trí đỗ P01 - P04
        existing_slots = db.query(ParkingSlot).count()
        if existing_slots == 0:
            slots = [
                ParkingSlot(slot_id=f"P0{i}", status="EMPTY", sensor_distance_cm=120.0, sensor_occupied=False, camera_occupied=False)
                for i in range(1, 5)
            ]
            db.add_all(slots)
            db.commit()
            logger.info("Created 4 parking slots: P01, P02, P03, P04")

        # 2. Thẻ RFID mẫu
        existing_cards = db.query(RFIDCard).count()
        if existing_cards == 0:
            demo_cards = [
                RFIDCard(card_uid="RFID-DEMO-01", owner_name="Nguyen Van An", vehicle_plate="30A-123.45", card_type="STANDARD"),
                RFIDCard(card_uid="RFID-DEMO-02", owner_name="Tran Thi Binh", vehicle_plate="29C-678.90", card_type="VIP"),
                RFIDCard(card_uid="RFID-DEMO-03", owner_name="Le Van Cuong", vehicle_plate="51F-345.67", card_type="STANDARD"),
                RFIDCard(card_uid="RFID-DEMO-04", owner_name="Pham Thi Dung", vehicle_plate="43A-888.88", card_type="STANDARD"),
            ]
            db.add_all(demo_cards)
            db.commit()
            logger.info("Created 4 demo RFID cards")

    @staticmethod
    def get_all_slots(db: Session):
        return db.query(ParkingSlot).order_by(ParkingSlot.slot_id).all()

    @staticmethod
    def get_available_slots_count(db: Session) -> int:
        return db.query(ParkingSlot).filter(ParkingSlot.status == "EMPTY").count()

    @staticmethod
    def calculate_fee(duration_minutes: int) -> int:
        """Tính phí đỗ xe:
        - Dưới 15 phút: Miễn phí (quick drop-off)
        - Giờ đầu tiên: 10.000 VNĐ
        - Mỗi giờ tiếp theo: 10.000 VNĐ
        """
        if duration_minutes <= 15:
            return 0
        hours = math.ceil(duration_minutes / 60.0)
        return max(settings.MINIMUM_FEE, hours * settings.HOURLY_RATE)

    @staticmethod
    async def process_entry_tap(db: Session, tap: CardTapRequest) -> GateTapResponse:
        """Quy tắc xử lý quẹt thẻ vào cổng (Check-in) với khóa đồng bộ tránh race conditions."""
        async with ParkingService._entry_lock:
            card = db.query(RFIDCard).filter(RFIDCard.card_uid == tap.card_uid).first()
            if not card or not card.is_active:
                reason = "CARD_INACTIVE" if card and not card.is_active else "CARD_UNKNOWN"
                msg = "Thẻ đã bị khóa hoặc ngừng kích hoạt." if reason == "CARD_INACTIVE" else "Thẻ không hợp lệ hoặc chưa từng đăng ký."
                await ws_manager.broadcast({
                    "event_type": "GATE_ACTION",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"gate_id": "ENTRY", "status": "REJECTED", "reason": reason, "card_uid": tap.card_uid}
                })
                return GateTapResponse(
                    status="REJECTED",
                    action="KEEP_CLOSED",
                    gate_id="ENTRY",
                    message=msg,
                    reason=reason
                )

            # Kiểm tra Anti-passback: Thẻ đang có phiên ACTIVE hay không
            active_session = db.query(ParkingSession).filter(
                ParkingSession.card_uid == tap.card_uid,
                ParkingSession.status == "ACTIVE"
            ).first()
            if active_session:
                return GateTapResponse(
                    status="REJECTED",
                    action="KEEP_CLOSED",
                    gate_id="ENTRY",
                    message="Thẻ đang có phiên gửi xe chưa hoàn tất (Anti-passback).",
                    reason="CARD_ALREADY_IN_USE"
                )

            # Kiểm tra bãi còn chỗ trống: Kiểm tra cả số phiên ACTIVE và ô EMPTY thực tế
            active_sessions_count = db.query(ParkingSession).filter(
                ParkingSession.status == "ACTIVE"
            ).count()
            available_slots = ParkingService.get_available_slots_count(db)

            if active_sessions_count >= 4 or available_slots <= 0:
                # Ghi nhận cảnh báo bãi đầy
                alert = SystemAlert(
                    alert_type="PARKING_FULL",
                    severity="WARNING",
                    message=f"Xe biển số {card.vehicle_plate} bị từ chối vào cổng do bãi đã đầy ({active_sessions_count}/4 xe đang gửi)."
                )
                db.add(alert)
                db.commit()
                await ws_manager.broadcast({
                    "event_type": "ALERT",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"type": "PARKING_FULL", "message": "Bãi đỗ xe đã đầy (0 chỗ trống)."}
                })
                return GateTapResponse(
                    status="REJECTED",
                    action="KEEP_CLOSED",
                    gate_id="ENTRY",
                    message="Bãi đỗ xe đã đầy. Không thể check-in.",
                    reason="PARKING_FULL"
                )

            # Tạo phiên gửi xe mới
            new_session = ParkingSession(
                card_uid=card.card_uid,
                vehicle_plate=card.vehicle_plate,
                entry_time=datetime.now(timezone.utc),
                status="ACTIVE"
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            # Mở barrier vào qua Hardware Adapter
            adapter = get_hardware_adapter()
            adapter.command_barrier("ENTRY", "OPEN")

            session_dto = ParkingSessionResponse.model_validate(new_session)
            await ws_manager.broadcast({
                "event_type": "SESSION_CREATED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session": session_dto.model_dump(),
                    "barrier_state": "OPEN",
                    "gate_id": "ENTRY"
                }
            })

            return GateTapResponse(
                status="ALLOWED",
                action="OPEN_BARRIER",
                gate_id="ENTRY",
                message=f"Chào mừng {card.owner_name} ({card.vehicle_plate})!",
                session=session_dto
            )

    @staticmethod
    async def process_exit_tap(db: Session, tap: CardTapRequest) -> GateTapResponse:
        """Quy tắc xử lý quẹt thẻ ra cổng (Check-out)."""
        card = db.query(RFIDCard).filter(RFIDCard.card_uid == tap.card_uid).first()
        if not card:
            return GateTapResponse(
                status="REJECTED",
                action="KEEP_CLOSED",
                gate_id="EXIT",
                message="Thẻ chưa từng đăng ký trong hệ thống.",
                reason="CARD_UNKNOWN"
            )

        if not card.is_active:
            return GateTapResponse(
                status="REJECTED",
                action="KEEP_CLOSED",
                gate_id="EXIT",
                message="Thẻ đã bị khóa hoặc ngừng kích hoạt.",
                reason="CARD_INACTIVE"
            )

        active_session = db.query(ParkingSession).filter(
            ParkingSession.card_uid == tap.card_uid,
            ParkingSession.status == "ACTIVE"
        ).order_by(ParkingSession.entry_time.desc()).first()

        if not active_session:
            return GateTapResponse(
                status="REJECTED",
                action="KEEP_CLOSED",
                gate_id="EXIT",
                message="Không tìm thấy phiên gửi xe hợp lệ cho thẻ này.",
                reason="NO_ACTIVE_SESSION"
            )

        exit_time = datetime.now(timezone.utc)
        entry_t = active_session.entry_time
        if entry_t.tzinfo is None:
            entry_t = entry_t.replace(tzinfo=timezone.utc)
        duration_minutes = max(1, int((exit_time - entry_t).total_seconds() / 60))
        fee = ParkingService.calculate_fee(duration_minutes)

        active_session.exit_time = exit_time
        active_session.duration_minutes = duration_minutes
        active_session.fee_amount = fee
        active_session.status = "COMPLETED"
        db.commit()
        db.refresh(active_session)

        # Mở barrier ra qua Hardware Adapter
        adapter = get_hardware_adapter()
        adapter.command_barrier("EXIT", "OPEN")

        session_dto = ParkingSessionResponse.model_validate(active_session)
        await ws_manager.broadcast({
            "event_type": "SESSION_COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "session": session_dto.model_dump(),
                "fee": fee,
                "duration_minutes": duration_minutes,
                "barrier_state": "OPEN",
                "gate_id": "EXIT"
            }
        })

        return GateTapResponse(
            status="ALLOWED",
            action="OPEN_BARRIER",
            gate_id="EXIT",
            message=f"Tạm biệt {card.owner_name}! Phí: {fee:,} VNĐ ({duration_minutes} phút)",
            session=session_dto
        )


    @staticmethod
    async def update_sensor_telemetry(db: Session, readings: list[SensorReading]):
        """Cập nhật dữ liệu từ cảm biến siêu âm ESP32 có xử lý trùng lặp cảnh báo."""
        ParkingService.last_sensor_telemetry_time = datetime.now(timezone.utc)
        updated = []
        for r in readings:
            slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == r.slot_id).first()
            if not slot:
                continue
            slot.sensor_distance_cm = r.distance_cm
            slot.sensor_occupied = r.occupied
            slot.updated_at = datetime.now(timezone.utc)

            # Kiểm tra sai lệch với camera
            has_mismatch = (slot.sensor_occupied != slot.camera_occupied)
            slot.has_mismatch = has_mismatch

            if has_mismatch:
                slot.status = "MISMATCH"
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
                        message=f"Bất thường tại ô {slot.slot_id}: Cảm biến báo {slot.sensor_occupied}, Camera báo {slot.camera_occupied}."
                    )
                    db.add(alert)
            else:
                slot.status = "OCCUPIED" if slot.sensor_occupied else "EMPTY"
                existing_alert = db.query(SystemAlert).filter(
                    SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
                    SystemAlert.slot_id == slot.slot_id,
                    SystemAlert.is_resolved == False
                ).first()
                if existing_alert:
                    existing_alert.is_resolved = True

            updated.append(slot)

        db.commit()

        # Phát sóng trạng thái mới lên WebSocket
        slots_payload = [
            {
                "slot_id": s.slot_id,
                "status": s.status,
                "sensor_distance_cm": s.sensor_distance_cm,
                "sensor_occupied": s.sensor_occupied,
                "camera_occupied": s.camera_occupied,
                "has_mismatch": s.has_mismatch
            }
            for s in updated
        ]
        await ws_manager.broadcast({
            "event_type": "SLOTS_BULK_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": slots_payload
        })

    @staticmethod
    async def update_vision_telemetry(db: Session, readings: list[VisionSlotReading]):
        """Cập nhật dữ liệu từ module nhận diện Camera AI với xử lý UNKNOWN/mất tín hiệu."""
        ParkingService.last_vision_telemetry_time = datetime.now(timezone.utc)
        updated = []
        for r in readings:
            slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == r.slot_id).first()
            if not slot:
                continue

            raw_state = (r.state or "").upper()
            if raw_state in ("UNKNOWN", "CAMERA_ERROR", "ERROR"):
                slot.status = "UNKNOWN"
                slot.camera_confidence = r.confidence
                slot.updated_at = datetime.now(timezone.utc)
                slot.has_mismatch = True

                existing_lost = db.query(SystemAlert).filter(
                    SystemAlert.alert_type == "CAMERA_SIGNAL_LOST",
                    SystemAlert.slot_id == slot.slot_id,
                    SystemAlert.is_resolved == False
                ).first()
                if not existing_lost:
                    alert = SystemAlert(
                        alert_type="CAMERA_SIGNAL_LOST",
                        slot_id=slot.slot_id,
                        severity="WARNING",
                        message=f"Tín hiệu camera tại {slot.slot_id} không xác định hoặc bị gián đoạn ({raw_state})."
                    )
                    db.add(alert)
            else:
                is_occupied = (raw_state == "OCCUPIED")
                slot.camera_occupied = is_occupied
                slot.camera_confidence = r.confidence
                slot.updated_at = datetime.now(timezone.utc)

                has_mismatch = (slot.sensor_occupied != slot.camera_occupied)
                slot.has_mismatch = has_mismatch

                if has_mismatch:
                    slot.status = "MISMATCH"
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
                            message=f"Thị giác AI tại {slot.slot_id} phát hiện trạng thái không khớp với cảm biến."
                        )
                        db.add(alert)
                else:
                    slot.status = "OCCUPIED" if slot.camera_occupied else "EMPTY"
                    existing_alert = db.query(SystemAlert).filter(
                        SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
                        SystemAlert.slot_id == slot.slot_id,
                        SystemAlert.is_resolved == False
                    ).first()
                    if existing_alert:
                        existing_alert.is_resolved = True

                existing_lost = db.query(SystemAlert).filter(
                    SystemAlert.alert_type == "CAMERA_SIGNAL_LOST",
                    SystemAlert.slot_id == slot.slot_id,
                    SystemAlert.is_resolved == False
                ).first()
                if existing_lost:
                    existing_lost.is_resolved = True

            updated.append(slot)

        db.commit()

        slots_payload = [
            {
                "slot_id": s.slot_id,
                "status": s.status,
                "camera_occupied": s.camera_occupied,
                "camera_confidence": s.camera_confidence,
                "has_mismatch": s.has_mismatch
            }
            for s in updated
        ]
        await ws_manager.broadcast({
            "event_type": "VISION_BULK_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": slots_payload
        })

    @staticmethod
    async def set_barrier_state(gate_id: str, state: str):
        adapter = get_hardware_adapter()
        adapter.command_barrier(gate_id, state)
        gate_info = adapter.get_barrier_status(gate_id)
        await ws_manager.broadcast({
            "event_type": "BARRIER_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "gate_id": gate_id.upper(),
                "state": gate_info["state"],
                "angle": gate_info["angle"],
                "obstruction": gate_info["obstruction"]
            }
        })

    @staticmethod
    async def command_barrier(db: Session, gate_id: str, command: str) -> tuple[bool, str]:
        """Điều khiển barrier có bảo vệ cảm biến an toàn."""
        adapter = get_hardware_adapter()
        success, message = adapter.command_barrier(gate_id, command)
        gate_info = adapter.get_barrier_status(gate_id)

        if not success and "SAFETY" in message:
            # Ghi nhận cảnh báo an toàn
            alert = SystemAlert(
                alert_type="BARRIER_OBSTRUCTION_DETECTED",
                slot_id=gate_id.upper(),
                severity="CRITICAL",
                message=f"[An toàn] Phát hiện vật cản tại {gate_id.upper()}! Hệ thống từ chối hạ cánh barie."
            )
            db.add(alert)
            db.commit()

            await ws_manager.broadcast({
                "event_type": "ALERT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "type": "BARRIER_OBSTRUCTION_DETECTED",
                    "gate_id": gate_id.upper(),
                    "message": message
                }
            })

        await ws_manager.broadcast({
            "event_type": "BARRIER_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "gate_id": gate_id.upper(),
                "state": gate_info["state"],
                "angle": gate_info["angle"],
                "obstruction": gate_info["obstruction"],
                "last_command": command,
                "success": success
            }
        })
        return success, message

    @staticmethod
    async def update_safety_sensor(db: Session, gate_id: str, has_obstruction: bool):
        adapter = get_hardware_adapter()
        adapter.set_safety_sensor(gate_id, has_obstruction)
        gate_info = adapter.get_barrier_status(gate_id)

        if has_obstruction and gate_info["state"] == "OPEN":
            # Có xe / người đứng trong vùng hạ barrier
            alert = SystemAlert(
                alert_type="SAFETY_BEAM_BLOCKED",
                slot_id=gate_id.upper(),
                severity="WARNING",
                message=f"Cảm biến an toàn tại cổng {gate_id.upper()} bị che chắn (xe đang đi qua hoặc dừng giữa cổng)."
            )
            db.add(alert)
            db.commit()

        await ws_manager.broadcast({
            "event_type": "SAFETY_SENSOR_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "gate_id": gate_id.upper(),
                "has_obstruction": has_obstruction,
                "state": gate_info["state"],
                "angle": gate_info["angle"]
            }
        })

    @staticmethod
    def get_system_stats(db: Session) -> dict:
        total = db.query(ParkingSlot).count()
        occupied = db.query(ParkingSlot).filter(ParkingSlot.status == "OCCUPIED").count()
        mismatch = db.query(ParkingSlot).filter(ParkingSlot.status == "MISMATCH").count()
        available = db.query(ParkingSlot).filter(ParkingSlot.status == "EMPTY").count()
        active_sessions = db.query(ParkingSession).filter(ParkingSession.status == "ACTIVE").count()
        total_rev = db.query(func.sum(ParkingSession.fee_amount)).filter(ParkingSession.status == "COMPLETED").scalar() or 0

        adapter = get_hardware_adapter()
        entry_gate = adapter.get_barrier_status("ENTRY")
        exit_gate = adapter.get_barrier_status("EXIT")

        now = datetime.now(timezone.utc)
        is_sim = (adapter.get_mode() == "SIMULATION")

        esp32_online = False
        if ParkingService.last_sensor_telemetry_time is not None:
            last_s = ParkingService.last_sensor_telemetry_time
            if last_s.tzinfo is None:
                last_s = last_s.replace(tzinfo=timezone.utc)
            esp32_online = (now - last_s).total_seconds() < 10.0
        elif is_sim:
            esp32_online = True

        camera_online = False
        if ParkingService.last_vision_telemetry_time is not None:
            last_v = ParkingService.last_vision_telemetry_time
            if last_v.tzinfo is None:
                last_v = last_v.replace(tzinfo=timezone.utc)
            camera_online = (now - last_v).total_seconds() < 10.0
        elif is_sim:
            camera_online = True

        return {
            "total_slots": total,
            "available_slots": available,
            "occupied_slots": occupied,
            "mismatch_slots": mismatch,
            "active_sessions_count": active_sessions,
            "total_revenue_vnd": int(total_rev),
            "barrier_entry_state": entry_gate.get("state", "CLOSED"),
            "barrier_exit_state": exit_gate.get("state", "CLOSED"),
            "barrier_entry_angle": entry_gate.get("angle", 0),
            "barrier_exit_angle": exit_gate.get("angle", 0),
            "barrier_entry_obstruction": entry_gate.get("obstruction", False),
            "barrier_exit_obstruction": exit_gate.get("obstruction", False),
            "is_simulation_mode": (adapter.get_mode() == "SIMULATION"),
            "system_mode": adapter.get_mode(),
            "esp32_online": esp32_online,
            "camera_online": camera_online
        }

