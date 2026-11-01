"""
HARDWARE ABSTRACTION LAYER (HAL)
Định nghĩa Interface chuẩn hoá giữa Core Backend và Lớp thiết bị (Edge Device).
Cho phép chuyển đổi liền mạch giữa SIMULATION MODE và PHYSICAL HARDWARE MODE (ESP32)
mà không cần thay đổi logic nghiệp vụ trung tâm.
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any

logger = logging.getLogger("hardware_adapter")

class IHardwareAdapter(ABC):
    """Giao diện trừu tượng hoá toàn bộ tương tác phần cứng Edge."""

    @abstractmethod
    def get_mode(self) -> str:
        """Trả về 'SIMULATION' hoặc 'HARDWARE'."""
        pass

    @abstractmethod
    def get_barrier_status(self, gate_id: str) -> Dict[str, Any]:
        """Trả về trạng thái barrier: {state: 'OPEN'|'CLOSED', angle: 0..90, obstruction: bool}"""
        pass

    @abstractmethod
    def set_barrier_state(self, gate_id: str, state: str, angle: Any = None) -> bool:
        """Cập nhật trạng thái cánh tay barie từ telemetry thiết bị hoặc logic điều khiển."""
        pass

    @abstractmethod
    def set_safety_sensor(self, gate_id: str, has_obstruction: bool) -> bool:
        """Cập nhật tín hiệu cảm biến quang an toàn tại cổng."""
        pass

    @abstractmethod
    def command_barrier(self, gate_id: str, action: str) -> tuple[bool, str]:
        """Ra lệnh mở/đóng barrier, trả về (thành_công, lý_do)."""
        pass

class SimulationHardwareAdapter(IHardwareAdapter):
    """
    Bộ chuyển đổi dành riêng cho chế độ mô phỏng phần mềm (FULL SOFTWARE SIMULATION).
    Duy trì trạng thái ảo của động cơ Servo, góc mở và cảm biến quang an toàn.
    """
    def __init__(self):
        self._gates = {
            "ENTRY": {
                "state": "CLOSED",
                "angle": 0,
                "obstruction": False
            },
            "EXIT": {
                "state": "CLOSED",
                "angle": 0,
                "obstruction": False
            }
        }
        logger.info("[HAL] Initialized SimulationHardwareAdapter (SIMULATION MODE)")

    def get_mode(self) -> str:
        return "SIMULATION"

    def get_barrier_status(self, gate_id: str) -> Dict[str, Any]:
        g = gate_id.upper()
        return self._gates.get(g, {"state": "CLOSED", "angle": 0, "obstruction": False})

    def set_barrier_state(self, gate_id: str, state: str, angle: Any = None) -> bool:
        g = gate_id.upper()
        if g in self._gates:
            st = state.upper()
            self._gates[g]["state"] = st
            if angle is not None:
                self._gates[g]["angle"] = int(angle)
            else:
                self._gates[g]["angle"] = 90 if st == "OPEN" else 0
            return True
        return False

    def set_safety_sensor(self, gate_id: str, has_obstruction: bool) -> bool:
        g = gate_id.upper()
        if g in self._gates:
            self._gates[g]["obstruction"] = has_obstruction
            logger.info(f"[SIMULATION HAL] Gate {g} Safety Sensor: Obstruction={'DETECTED' if has_obstruction else 'CLEAR'}")
            return True
        return False

    def command_barrier(self, gate_id: str, action: str) -> tuple[bool, str]:
        g = gate_id.upper()
        act = action.upper()
        if g not in self._gates:
            return False, f"Unknown gate ID: {gate_id}"

        gate_data = self._gates[g]

        if act == "OPEN":
            gate_data["state"] = "OPEN"
            gate_data["angle"] = 90
            logger.info(f"[SIMULATION HAL] Gate {g}: Servo rotated to 90 degrees (OPEN)")
            return True, "Barrier opened successfully (90 degrees)"

        elif act == "CLOSE":
            # QUY TẮC AN TOÀN: Không được đóng barrier khi còn vật cản trong vùng quét
            if gate_data["obstruction"]:
                logger.warning(f"[SIMULATION HAL] Gate {g}: Close rejected! Obstruction detected in safety line.")
                return False, "SAFETY REJECTION: Obstruction detected in barrier clearance zone!"

            gate_data["state"] = "CLOSED"
            gate_data["angle"] = 0
            logger.info(f"[SIMULATION HAL] Gate {g}: Servo rotated to 0 degrees (CLOSED)")
            return True, "Barrier closed successfully (0 degrees)"

        return False, f"Invalid barrier action: {action}"

class PhysicalHardwareAdapter(IHardwareAdapter):
    """
    Bộ chuyển đổi kết nối với vi điều khiển ESP32 thật qua giao thức MQTT / REST.
    Duy trì trạng thái thực tế nhận được từ telemetry của ESP32 (POST /gate/barrier-state và /gate/safety-sensor).
    Tách biệt quyết định cho phép truy cập với trạng thái vật lý thực tế của cơ cấu chấp hành.
    """
    def __init__(self, broker_url: str = "mqtt://localhost:1883"):
        self.broker_url = broker_url
        self._gates = {
            "ENTRY": {
                "state": "CLOSED",
                "angle": 0,
                "obstruction": False
            },
            "EXIT": {
                "state": "CLOSED",
                "angle": 0,
                "obstruction": False
            }
        }
        logger.info(f"[HAL] Initialized PhysicalHardwareAdapter (HARDWARE MODE, Broker: {broker_url})")

    def get_mode(self) -> str:
        return "HARDWARE"

    def get_barrier_status(self, gate_id: str) -> Dict[str, Any]:
        g = gate_id.upper()
        return self._gates.get(g, {"state": "CLOSED", "angle": 0, "obstruction": False})

    def set_barrier_state(self, gate_id: str, state: str, angle: Any = None) -> bool:
        g = gate_id.upper()
        if g in self._gates:
            st = state.upper()
            self._gates[g]["state"] = st
            if angle is not None:
                self._gates[g]["angle"] = int(angle)
            else:
                self._gates[g]["angle"] = 90 if st == "OPEN" else 0
            logger.info(f"[PHYSICAL HAL] Gate {g} reported barrier state: state={st}, angle={self._gates[g]['angle']}")
            return True
        return False

    def set_safety_sensor(self, gate_id: str, has_obstruction: bool) -> bool:
        g = gate_id.upper()
        if g in self._gates:
            self._gates[g]["obstruction"] = bool(has_obstruction)
            logger.info(f"[PHYSICAL HAL] Gate {g} reported safety sensor: obstruction={has_obstruction}")
            return True
        return False

    def command_barrier(self, gate_id: str, action: str) -> tuple[bool, str]:
        g = gate_id.upper()
        act = action.upper()
        if g not in self._gates:
            return False, f"Unknown gate ID: {gate_id}"
        if act == "CLOSE" and self._gates[g]["obstruction"]:
            logger.warning(f"[PHYSICAL HAL] Gate {g}: Close command rejected! Obstruction detected.")
            return False, "SAFETY REJECTION: Obstruction detected in barrier clearance zone!"
        logger.info(f"[PHYSICAL HAL] Dispatching command '{act}' to ESP32 for gate {g}")
        return True, f"Hardware command {act} dispatched to ESP32"

# Global Adapter Instance
_current_adapter = SimulationHardwareAdapter()

def get_hardware_adapter() -> IHardwareAdapter:
    global _current_adapter
    return _current_adapter

def set_hardware_mode(mode: str) -> IHardwareAdapter:
    global _current_adapter
    if mode.upper() == "HARDWARE":
        _current_adapter = PhysicalHardwareAdapter()
    else:
        _current_adapter = SimulationHardwareAdapter()
    return _current_adapter
