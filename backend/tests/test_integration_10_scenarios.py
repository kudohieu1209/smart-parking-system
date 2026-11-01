"""Automated End-to-End Integration Tests for SMART-PARKING-SYSTEM
Covers all 10 Phase 2 Scenarios:
- TEST 01: Normal Entry Flow (Check-in, barrier open, slot parking)
- TEST 02: Invalid/Unknown RFID Card Handling
- TEST 03: Parking Full (Capacity 4 limit enforcement)
- TEST 04: Anti-passback Prevention (Double check-in blocked)
- TEST 05: Exit & Tiered Fee Calculation (<15m free, <=1h, >1h)
- TEST 06: Ultrasonic Sensor & Camera AI Mismatch & Deduplication
- TEST 07: Barrier Safety Interlock (Optical Obstruction Beam)
- TEST 08: ESP32 Telemetry Watchdog / Stale Timeout Detection
- TEST 09: Camera AI Signal Loss / Degraded Frame Handling
- TEST 10: High Concurrency Race Condition Protection
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.parking import ParkingSlot, RFIDCard, ParkingSession, SystemAlert
from backend.app.schemas.parking import CardTapRequest
from backend.app.services.parking_service import ParkingService
from backend.app.core.hardware_adapter import get_hardware_adapter, set_hardware_mode


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_database():
    """Reset the database and hardware state before each integration test."""
    set_hardware_mode("SIMULATION")
    db = SessionLocal()
    try:
        # Clear sessions and alerts
        db.query(ParkingSession).delete()
        db.query(SystemAlert).delete()

        # Seed or ensure initial slots and demo cards exist
        ParkingService.seed_initial_data(db)

        # Reset all slots to EMPTY
        slots = db.query(ParkingSlot).all()
        for s in slots:
            s.status = "EMPTY"
            s.sensor_distance_cm = 120.0
            s.sensor_occupied = False
            s.camera_occupied = False
            s.camera_confidence = 1.0
            s.has_mismatch = False

        # Reset barriers
        adapter = get_hardware_adapter()
        adapter.set_safety_sensor("ENTRY", False)
        adapter.set_safety_sensor("EXIT", False)
        adapter.command_barrier("ENTRY", "CLOSE")
        adapter.command_barrier("EXIT", "CLOSE")

        # Reset telemetry timestamps
        ParkingService.last_sensor_telemetry_time = None
        ParkingService.last_vision_telemetry_time = None

        db.commit()
    finally:
        db.close()


# ==============================================================================
# TEST 01: Normal Entry Flow
# ==============================================================================
def test_01_normal_entry_flow(client):
    """Test standard check-in flow: tap demo card -> barrier opens -> slot occupied -> available slots decrements."""
    # 1. Verify 4 slots initially available
    slots_resp = client.get("/api/v1/slots")
    assert slots_resp.status_code == 200
    assert slots_resp.json()["available_slots"] == 4

    # 2. Tap RFID-DEMO-01 at entry gate
    entry_payload = {"card_uid": "RFID-DEMO-01", "gate_id": "ENTRY"}
    entry_resp = client.post("/api/v1/gate/entry-tap", json=entry_payload)
    assert entry_resp.status_code == 200
    entry_data = entry_resp.json()
    assert entry_data["status"] == "ALLOWED"
    assert entry_data["action"] == "OPEN_BARRIER"
    assert entry_data["session"]["status"] == "ACTIVE"

    # Verify barrier opened
    stats_resp = client.get("/api/v1/system/stats")
    assert stats_resp.json()["barrier_entry_state"] == "OPEN"

    # 3. Simulate car passing through gate (safety sensor activates then clears)
    client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": True})
    client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": False})
    client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"})

    # 4. Simulate car parking into slot P01 (sensor reports 15.0cm occupied)
    sensor_payload = {
        "device_id": "ESP32_CORE_01",
        "readings": [
            {"slot_id": "P01", "distance_cm": 15.0, "occupied": True},
            {"slot_id": "P02", "distance_cm": 120.0, "occupied": False},
            {"slot_id": "P03", "distance_cm": 120.0, "occupied": False},
            {"slot_id": "P04", "distance_cm": 120.0, "occupied": False},
        ]
    }
    vision_payload = {
        "camera_id": "CAM_MAIN_01",
        "slots": [
            {"slot_id": "P01", "state": "OCCUPIED", "confidence": 0.98},
            {"slot_id": "P02", "state": "EMPTY", "confidence": 0.99},
            {"slot_id": "P03", "state": "EMPTY", "confidence": 0.99},
            {"slot_id": "P04", "state": "EMPTY", "confidence": 0.99},
        ]
    }
    client.post("/api/v1/telemetry/sensors", json=sensor_payload)
    client.post("/api/v1/telemetry/vision", json=vision_payload)

    # 5. Verify system state: P01 OCCUPIED, available slots = 3
    slots_after = client.get("/api/v1/slots").json()
    assert slots_after["available_slots"] == 3
    assert slots_after["occupied_slots"] == 1
    p01 = next(s for s in slots_after["slots"] if s["slot_id"] == "P01")
    assert p01["status"] == "OCCUPIED"
    assert p01["sensor_occupied"] is True
    assert p01["camera_occupied"] is True


# ==============================================================================
# TEST 02: Invalid / Unknown RFID
# ==============================================================================
def test_02_invalid_rfid(client):
    """Test that unauthorized cards are rejected, no session created, barrier stays closed."""
    payload = {"card_uid": "RFID-ROGUE-9999", "gate_id": "ENTRY"}
    resp = client.post("/api/v1/gate/entry-tap", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "REJECTED"
    assert data["action"] == "KEEP_CLOSED"
    assert data["reason"] == "CARD_UNKNOWN"
    assert data["session"] is None

    # Check database: no sessions created
    db = SessionLocal()
    assert db.query(ParkingSession).count() == 0
    db.close()

    # Barrier must remain closed
    stats = client.get("/api/v1/system/stats").json()
    assert stats["barrier_entry_state"] == "CLOSED"


# ==============================================================================
# TEST 03: Parking Full Limit (Capacity = 4)
# ==============================================================================
def test_03_parking_full(client):
    """Test parking full scenario: 4 cars check in, 5th card is rejected with PARKING_FULL."""
    db = SessionLocal()
    # Ensure 5 demo cards exist
    card_5 = db.query(RFIDCard).filter(RFIDCard.card_uid == "RFID-DEMO-05").first()
    if not card_5:
        card_5 = RFIDCard(card_uid="RFID-DEMO-05", owner_name="Hoang Van Em", vehicle_plate="50Z-999.99", card_type="STANDARD")
        db.add(card_5)
        db.commit()
    db.close()

    # Check-in 4 valid cars
    cards = ["RFID-DEMO-01", "RFID-DEMO-02", "RFID-DEMO-03", "RFID-DEMO-04"]
    for c_uid in cards:
        r = client.post("/api/v1/gate/entry-tap", json={"card_uid": c_uid, "gate_id": "ENTRY"})
        assert r.status_code == 200
        assert r.json()["status"] == "ALLOWED"

    # Attempt 5th check-in -> Must be REJECTED with PARKING_FULL
    fifth_resp = client.post("/api/v1/gate/entry-tap", json={"card_uid": "RFID-DEMO-05", "gate_id": "ENTRY"})
    assert fifth_resp.status_code == 200
    fifth_data = fifth_resp.json()
    assert fifth_data["status"] == "REJECTED"
    assert fifth_data["reason"] == "PARKING_FULL"
    assert fifth_data["action"] == "KEEP_CLOSED"

    # Verify PARKING_FULL alert was logged
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert any(a["alert_type"] == "PARKING_FULL" for a in alerts)


# ==============================================================================
# TEST 04: Anti-passback Protection
# ==============================================================================
def test_04_anti_passback(client):
    """Test that a card currently checked in cannot tap entry again."""
    entry_payload = {"card_uid": "RFID-DEMO-01", "gate_id": "ENTRY"}
    # First tap -> ALLOWED
    r1 = client.post("/api/v1/gate/entry-tap", json=entry_payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "ALLOWED"

    # Second tap with same card -> REJECTED with CARD_ALREADY_IN_USE
    r2 = client.post("/api/v1/gate/entry-tap", json=entry_payload)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "REJECTED"
    assert data2["reason"] == "CARD_ALREADY_IN_USE"
    assert data2["action"] == "KEEP_CLOSED"

    # Only 1 active session in database
    db = SessionLocal()
    active_count = db.query(ParkingSession).filter(
        ParkingSession.card_uid == "RFID-DEMO-01",
        ParkingSession.status == "ACTIVE"
    ).count()
    assert active_count == 1
    db.close()


# ==============================================================================
# TEST 05: Exit & Tiered Fee Calculation
# ==============================================================================
def test_05_exit_and_fee_calculation(client):
    """Test checkout fee structure:
    - Tier A: <= 15 minutes -> 0 VND (free grace period)
    - Tier B: 40 minutes (<= 1 hour) -> 10,000 VND
    - Tier C: 130 minutes (2h 10m -> ceil = 3h) -> 30,000 VND
    """
    db = SessionLocal()

    # Tier A: 10 minutes ago
    s_a = ParkingSession(
        card_uid="RFID-DEMO-01",
        vehicle_plate="30A-123.45",
        entry_time=datetime.now(timezone.utc) - timedelta(minutes=10),
        status="ACTIVE"
    )
    # Tier B: 40 minutes ago
    s_b = ParkingSession(
        card_uid="RFID-DEMO-02",
        vehicle_plate="29C-678.90",
        entry_time=datetime.now(timezone.utc) - timedelta(minutes=40),
        status="ACTIVE"
    )
    # Tier C: 130 minutes ago
    s_c = ParkingSession(
        card_uid="RFID-DEMO-03",
        vehicle_plate="51F-345.67",
        entry_time=datetime.now(timezone.utc) - timedelta(minutes=130),
        status="ACTIVE"
    )
    db.add_all([s_a, s_b, s_c])
    db.commit()
    db.close()

    # Checkout Tier A
    resp_a = client.post("/api/v1/gate/exit-tap", json={"card_uid": "RFID-DEMO-01", "gate_id": "EXIT"})
    assert resp_a.status_code == 200
    assert resp_a.json()["session"]["fee_amount"] == 0
    assert resp_a.json()["session"]["status"] == "COMPLETED"

    # Checkout Tier B
    resp_b = client.post("/api/v1/gate/exit-tap", json={"card_uid": "RFID-DEMO-02", "gate_id": "EXIT"})
    assert resp_b.status_code == 200
    assert resp_b.json()["session"]["fee_amount"] == 10000
    assert resp_b.json()["session"]["status"] == "COMPLETED"

    # Checkout Tier C
    resp_c = client.post("/api/v1/gate/exit-tap", json={"card_uid": "RFID-DEMO-03", "gate_id": "EXIT"})
    assert resp_c.status_code == 200
    assert resp_c.json()["session"]["fee_amount"] == 30000
    assert resp_c.json()["session"]["status"] == "COMPLETED"


# ==============================================================================
# TEST 06: Ultrasonic Sensor & Camera AI Mismatch & Deduplication
# ==============================================================================
def test_06_sensor_camera_mismatch(client):
    """Test mismatch detection between HC-SR04 ultrasonic sensor and Camera AI.
    Ensure alert is generated, repeated ticks DO NOT flood duplicates, and resolving restores status.
    """
    # 1. Ultrasonic reports P02 OCCUPIED (18cm)
    client.post("/api/v1/telemetry/sensors", json={
        "device_id": "ESP32_CORE_01",
        "readings": [{"slot_id": "P02", "distance_cm": 18.0, "occupied": True}]
    })

    # 2. Camera reports P02 EMPTY
    client.post("/api/v1/telemetry/vision", json={
        "camera_id": "CAM_MAIN_01",
        "slots": [{"slot_id": "P02", "state": "EMPTY", "confidence": 0.95}]
    })

    # Verify P02 status is MISMATCH
    slots = client.get("/api/v1/slots").json()
    p02 = next(s for s in slots["slots"] if s["slot_id"] == "P02")
    assert p02["status"] == "MISMATCH"
    assert p02["has_mismatch"] is True

    # 3. Repeat telemetry ticks 3 times -> Alert flood check
    for _ in range(3):
        client.post("/api/v1/telemetry/sensors", json={
            "device_id": "ESP32_CORE_01",
            "readings": [{"slot_id": "P02", "distance_cm": 18.0, "occupied": True}]
        })

    db = SessionLocal()
    unresolved_alerts = db.query(SystemAlert).filter(
        SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
        SystemAlert.slot_id == "P02",
        SystemAlert.is_resolved == False
    ).all()
    # Must only have 1 active alert, NOT flooded with 4
    assert len(unresolved_alerts) == 1
    db.close()

    # 4. Resolve mismatch: Camera now sees the vehicle
    client.post("/api/v1/telemetry/vision", json={
        "camera_id": "CAM_MAIN_01",
        "slots": [{"slot_id": "P02", "state": "OCCUPIED", "confidence": 0.96}]
    })

    slots_after = client.get("/api/v1/slots").json()
    p02_after = next(s for s in slots_after["slots"] if s["slot_id"] == "P02")
    assert p02_after["status"] == "OCCUPIED"
    assert p02_after["has_mismatch"] is False

    # Check alert auto-resolved
    db = SessionLocal()
    active_alerts = db.query(SystemAlert).filter(
        SystemAlert.alert_type == "SENSOR_CAMERA_MISMATCH",
        SystemAlert.slot_id == "P02",
        SystemAlert.is_resolved == False
    ).count()
    assert active_alerts == 0
    db.close()


# ==============================================================================
# TEST 07: Barrier Safety Interlock
# ==============================================================================
def test_07_barrier_safety_interlock(client):
    """Test safety sensor interlock preventing barrier closing onto vehicles."""
    # 1. Open ENTRY barrier
    resp_open = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "OPEN"})
    assert resp_open.status_code == 200

    # 2. Obstruction detected in barrier zone
    client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": True})

    # 3. Attempt to CLOSE barrier -> Must be rejected with 400
    resp_close_fail = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"})
    assert resp_close_fail.status_code == 400
    assert "SAFETY" in resp_close_fail.json()["detail"]

    # Barrier must still be OPEN
    stats = client.get("/api/v1/system/stats").json()
    assert stats["barrier_entry_state"] == "OPEN"
    assert stats["barrier_entry_obstruction"] is True

    # 4. Clear obstruction
    client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": False})

    # 5. Now close command succeeds
    resp_close_ok = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"})
    assert resp_close_ok.status_code == 200
    stats_after = client.get("/api/v1/system/stats").json()
    assert stats_after["barrier_entry_state"] == "CLOSED"


# ==============================================================================
# TEST 08: ESP32 Telemetry Watchdog / Stale Detection
# ==============================================================================
def test_08_esp32_telemetry_timeout(client):
    """Test heartbeat watchdog: stale telemetry (>10s) marks ESP32 as offline."""
    # 1. Send fresh telemetry
    client.post("/api/v1/telemetry/sensors", json={
        "device_id": "ESP32_CORE_01",
        "readings": [{"slot_id": "P01", "distance_cm": 120.0, "occupied": False}]
    })
    stats_fresh = client.get("/api/v1/system/stats").json()
    assert stats_fresh["esp32_online"] is True

    # 2. Backdate telemetry timestamp by 15 seconds
    ParkingService.last_sensor_telemetry_time = datetime.now(timezone.utc) - timedelta(seconds=15)

    stats_stale = client.get("/api/v1/system/stats").json()
    assert stats_stale["esp32_online"] is False

    # 3. New telemetry restores online status
    client.post("/api/v1/telemetry/sensors", json={
        "device_id": "ESP32_CORE_01",
        "readings": [{"slot_id": "P01", "distance_cm": 120.0, "occupied": False}]
    })
    stats_recovered = client.get("/api/v1/system/stats").json()
    assert stats_recovered["esp32_online"] is True


# ==============================================================================
# TEST 09: Camera AI Signal Loss / UNKNOWN Handling
# ==============================================================================
def test_09_camera_signal_loss(client):
    """Test handling of degraded frames / UNKNOWN / CAMERA_ERROR states from camera stream."""
    # Send vision telemetry with UNKNOWN status
    client.post("/api/v1/telemetry/vision", json={
        "camera_id": "CAM_MAIN_01",
        "slots": [{"slot_id": "P03", "state": "CAMERA_ERROR", "confidence": 0.0}]
    })

    # Slot must be marked UNKNOWN (not falsely set to EMPTY)
    slots = client.get("/api/v1/slots").json()
    p03 = next(s for s in slots["slots"] if s["slot_id"] == "P03")
    assert p03["status"] == "UNKNOWN"

    # CAMERA_SIGNAL_LOST alert generated
    alerts = client.get("/api/v1/alerts").json()
    assert any(a["alert_type"] == "CAMERA_SIGNAL_LOST" and a["slot_id"] == "P03" for a in alerts)

    # Recovery: camera comes back online
    client.post("/api/v1/telemetry/vision", json={
        "camera_id": "CAM_MAIN_01",
        "slots": [{"slot_id": "P03", "state": "EMPTY", "confidence": 0.99}]
    })
    slots_rec = client.get("/api/v1/slots").json()
    p03_rec = next(s for s in slots_rec["slots"] if s["slot_id"] == "P03")
    assert p03_rec["status"] == "EMPTY"


# ==============================================================================
# TEST 10: High Concurrency Race Condition Protection
# ==============================================================================
def test_10_high_concurrency_race_condition():
    """Test concurrent check-in taps with asyncio.gather to verify mutex lock prevents over-allocation."""
    async def run_concurrent_test():
        db = SessionLocal()
        # Ensure 8 cards are seeded
        cards = []
        for i in range(1, 9):
            uid = f"RFID-CONCUR-{i:02d}"
            c = db.query(RFIDCard).filter(RFIDCard.card_uid == uid).first()
            if not c:
                c = RFIDCard(card_uid=uid, owner_name=f"Driver {i}", vehicle_plate=f"29A-{i*111:03d}.00", card_type="STANDARD")
                db.add(c)
            cards.append(uid)
        db.commit()
        db.close()

        # Issue 8 concurrent entry tap tasks using independent DB sessions
        async def simulate_tap(c_uid: str):
            session_db = SessionLocal()
            try:
                req = CardTapRequest(card_uid=c_uid, gate_id="ENTRY")
                return await ParkingService.process_entry_tap(session_db, req)
            finally:
                session_db.close()

        results = await asyncio.gather(*(simulate_tap(uid) for uid in cards))

        allowed_count = sum(1 for r in results if r.status == "ALLOWED")
        rejected_count = sum(1 for r in results if r.status == "REJECTED")

        # Parking lot capacity is strictly 4: exactly 4 allowed, 4 rejected!
        assert allowed_count == 4
        assert rejected_count == 4
        for r in results:
            if r.status == "REJECTED":
                assert r.reason == "PARKING_FULL"

        # Database verification
        verify_db = SessionLocal()
        active_in_db = verify_db.query(ParkingSession).filter(ParkingSession.status == "ACTIVE").count()
        assert active_in_db == 4
        verify_db.close()

    asyncio.run(run_concurrent_test())


# ==============================================================================
# TEST 11: Wokwi & Hardware Standardized Hex RFID Card Formats
# ==============================================================================
def test_11_wokwi_standardized_hex_rfid_cards(client):
    """Test standardized 4-byte hexadecimal RFID UIDs (both colon and plain hex) in Wokwi & hardware mode."""
    # 1. Entry tap with colon format "30:A1:23:45"
    resp = client.post("/api/v1/gate/entry-tap", json={"card_uid": "30:A1:23:45", "gate_id": "ENTRY"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ALLOWED"
    assert data["action"] == "OPEN_BARRIER"
    assert data["session"]["status"] == "ACTIVE"

    # 2. Anti-passback test using plain hex format without colons "30A12345"
    resp_dup = client.post("/api/v1/gate/entry-tap", json={"card_uid": "30A12345", "gate_id": "ENTRY"})
    assert resp_dup.status_code == 200
    data_dup = resp_dup.json()
    assert data_dup["status"] == "REJECTED"
    assert data_dup["reason"] == "CARD_ALREADY_IN_USE"

    # 3. Exit tap with plain hex format "30A12345"
    resp_exit = client.post("/api/v1/gate/exit-tap", json={"card_uid": "30A12345", "gate_id": "EXIT"})
    assert resp_exit.status_code == 200
    data_exit = resp_exit.json()
    assert data_exit["status"] == "ALLOWED"
    assert data_exit["action"] == "OPEN_BARRIER"
    assert data_exit["session"]["status"] == "COMPLETED"

    # 4. Entry and exit tap with second hardware/Wokwi card "01:02:03:04"
    resp_entry2 = client.post("/api/v1/gate/entry-tap", json={"card_uid": "01:02:03:04", "gate_id": "ENTRY"})
    assert resp_entry2.status_code == 200
    assert resp_entry2.json()["status"] == "ALLOWED"
    assert resp_entry2.json()["action"] == "OPEN_BARRIER"

    resp_exit2 = client.post("/api/v1/gate/exit-tap", json={"card_uid": "01:02:03:04", "gate_id": "EXIT"})
    assert resp_exit2.status_code == 200
    assert resp_exit2.json()["status"] == "ALLOWED"
    assert resp_exit2.json()["action"] == "OPEN_BARRIER"
    assert resp_exit2.json()["session"]["status"] == "COMPLETED"

