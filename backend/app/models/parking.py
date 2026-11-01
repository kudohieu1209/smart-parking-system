from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def utc_now():
    return datetime.now(timezone.utc)

class RFIDCard(Base):
    __tablename__ = "rfid_cards"

    card_uid = Column(String(32), primary_key=True, index=True)
    owner_name = Column(String(100), nullable=False)
    vehicle_plate = Column(String(20), nullable=False, index=True)
    card_type = Column(String(20), default="STANDARD")  # STANDARD, VIP, MONTHLY
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    sessions = relationship("ParkingSession", back_populates="card")

class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    slot_id = Column(String(10), primary_key=True)  # P01, P02, P03, P04
    status = Column(String(20), default="EMPTY")     # EMPTY, OCCUPIED, MISMATCH, DISABLED
    sensor_distance_cm = Column(Float, default=100.0)
    sensor_occupied = Column(Boolean, default=False)
    camera_occupied = Column(Boolean, default=False)
    camera_confidence = Column(Float, default=1.0)
    has_mismatch = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    sessions = relationship("ParkingSession", back_populates="slot")

class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    card_uid = Column(String(32), ForeignKey("rfid_cards.card_uid"), nullable=False, index=True)
    vehicle_plate = Column(String(20), nullable=True)
    slot_id = Column(String(10), ForeignKey("parking_slots.slot_id"), nullable=True)
    entry_time = Column(DateTime, default=utc_now, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    fee_amount = Column(Integer, default=0)
    status = Column(String(20), default="ACTIVE", index=True)  # ACTIVE, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)

    card = relationship("RFIDCard", back_populates="sessions")
    slot = relationship("ParkingSlot", back_populates="sessions")

class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)  # MISMATCH, SENSOR_FAULT, GATE_OBSTRUCTION, PARKING_FULL
    slot_id = Column(String(10), nullable=True)
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

