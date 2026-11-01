import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert data["mode"] == "SIMULATION"

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_get_slots(client):
    response = client.get("/api/v1/slots")
    assert response.status_code == 200
    data = response.json()
    assert data["total_slots"] == 4
    assert len(data["slots"]) == 4
    slot_ids = [s["slot_id"] for s in data["slots"]]
    assert "P01" in slot_ids
    assert "P04" in slot_ids

def test_entry_and_exit_tap_flow(client):
    # Ensure any lingering test session for this card is cleaned up
    from backend.app.database.session import SessionLocal
    from backend.app.models.parking import ParkingSession
    db = SessionLocal()
    db.query(ParkingSession).filter(ParkingSession.card_uid == "RFID-DEMO-01").delete()
    db.commit()
    db.close()

    # 1. Entry tap with demo card
    entry_payload = {"card_uid": "RFID-DEMO-01", "gate_id": "ENTRY"}
    entry_resp = client.post("/api/v1/gate/entry-tap", json=entry_payload)
    assert entry_resp.status_code == 200
    entry_data = entry_resp.json()
    assert entry_data["status"] == "ALLOWED"
    assert entry_data["action"] == "OPEN_BARRIER"
    assert entry_data["session"]["status"] == "ACTIVE"

    # 2. Try duplicate tap (anti-passback test)
    dup_resp = client.post("/api/v1/gate/entry-tap", json=entry_payload)
    assert dup_resp.status_code == 200
    assert dup_resp.json()["status"] == "REJECTED"
    assert dup_resp.json()["reason"] == "CARD_ALREADY_IN_USE"

    # 3. Exit tap with demo card
    exit_payload = {"card_uid": "RFID-DEMO-01", "gate_id": "EXIT"}
    exit_resp = client.post("/api/v1/gate/exit-tap", json=exit_payload)
    assert exit_resp.status_code == 200
    exit_data = exit_resp.json()
    assert exit_data["status"] == "ALLOWED"
    assert exit_data["action"] == "OPEN_BARRIER"
    assert exit_data["session"]["status"] == "COMPLETED"

def test_simulator_slot_toggle(client):
    # Toggle P02 to OCCUPIED
    toggle_payload = {"slot_id": "P02", "occupied": True}
    resp = client.post("/api/v1/simulator/slot-toggle", json=toggle_payload)
    assert resp.status_code == 200

    slots_resp = client.get("/api/v1/slots")
    p02 = next(s for s in slots_resp.json()["slots"] if s["slot_id"] == "P02")
    assert p02["status"] == "OCCUPIED"
    assert p02["sensor_occupied"] is True

    # Reset slots
    client.post("/api/v1/simulator/reset")
    slots_resp_after = client.get("/api/v1/slots")
    p02_after = next(s for s in slots_resp_after.json()["slots"] if s["slot_id"] == "P02")
    assert p02_after["status"] == "EMPTY"

def test_simulator_inject_mismatch(client):
    mismatch_payload = {"slot_id": "P03", "sensor_occupied": True, "camera_occupied": False}
    resp = client.post("/api/v1/simulator/inject-mismatch", json=mismatch_payload)
    assert resp.status_code == 200

    slots_resp = client.get("/api/v1/slots")
    p03 = next(s for s in slots_resp.json()["slots"] if s["slot_id"] == "P03")
    assert p03["status"] == "MISMATCH"
    assert p03["has_mismatch"] is True

def test_barrier_safety_and_commands(client):
    # 1. Open entry barrier
    cmd_open = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "OPEN"})
    assert cmd_open.status_code == 200

    # 2. Simulate safety sensor detecting obstruction (car in gateway)
    safety_resp = client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": True})
    assert safety_resp.status_code == 200

    # 3. Attempt to close barrier -> Must be rejected due to safety obstruction
    cmd_close_blocked = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"})
    assert cmd_close_blocked.status_code == 400
    assert "SAFETY" in cmd_close_blocked.json()["detail"]

    # 4. Clear safety obstruction -> Close command must now succeed
    client.post("/api/v1/gate/safety-sensor", json={"gate_id": "ENTRY", "has_obstruction": False})
    cmd_close_ok = client.post("/api/v1/gate/command", json={"gate_id": "ENTRY", "command": "CLOSE"})
    assert cmd_close_ok.status_code == 200

def test_card_toggle_active(client):
    # 1. Deactivate demo card 02
    resp = client.post("/api/v1/cards/toggle-active", json={"card_uid": "RFID-DEMO-02", "is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 2. Tap with deactivated card -> must be rejected with CARD_INACTIVE
    tap_resp = client.post("/api/v1/gate/entry-tap", json={"card_uid": "RFID-DEMO-02", "gate_id": "ENTRY"})
    assert tap_resp.status_code == 200
    assert tap_resp.json()["status"] == "REJECTED"
    assert tap_resp.json()["reason"] == "CARD_INACTIVE"

    # 3. Re-activate card
    reactivate = client.post("/api/v1/cards/toggle-active", json={"card_uid": "RFID-DEMO-02", "is_active": True})
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True

def test_system_mode_toggle(client):
    # Check default mode
    mode_resp = client.get("/api/v1/system/mode")
    assert mode_resp.status_code == 200
    assert mode_resp.json()["mode"] == "SIMULATION"

    # Toggle to HARDWARE
    set_hw = client.post("/api/v1/system/mode?mode=HARDWARE")
    assert set_hw.status_code == 200
    assert set_hw.json()["mode"] == "HARDWARE"

    # Toggle back to SIMULATION
    set_sim = client.post("/api/v1/system/mode?mode=SIMULATION")
    assert set_sim.status_code == 200
    assert set_sim.json()["mode"] == "SIMULATION"

