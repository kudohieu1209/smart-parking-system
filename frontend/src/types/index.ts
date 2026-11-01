export interface ParkingSlot {
  slot_id: string;
  status: 'EMPTY' | 'OCCUPIED' | 'MISMATCH' | 'DISABLED';
  sensor_distance_cm: number;
  sensor_occupied: boolean;
  camera_occupied: boolean;
  camera_confidence: number;
  has_mismatch: boolean;
  updated_at?: string;
}

export interface SlotListResponse {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  mismatch_slots: number;
  slots: ParkingSlot[];
}

export interface SystemStats {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  mismatch_slots: number;
  active_sessions_count: number;
  total_revenue_vnd: number;
  barrier_entry_state: 'OPEN' | 'CLOSED';
  barrier_exit_state: 'OPEN' | 'CLOSED';
  barrier_entry_angle: number;
  barrier_exit_angle: number;
  barrier_entry_obstruction: boolean;
  barrier_exit_obstruction: boolean;
  is_simulation_mode: boolean;
  system_mode: string;
  esp32_online?: boolean;
  camera_online?: boolean;
}


export interface ParkingSession {
  id: number;
  card_uid: string;
  vehicle_plate?: string;
  slot_id?: string;
  entry_time: string;
  exit_time?: string;
  duration_minutes: number;
  fee_amount: number;
  status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  notes?: string;
}

export interface RFIDCard {
  card_uid: string;
  owner_name: string;
  vehicle_plate: string;
  card_type: string;
  is_active: boolean;
  created_at?: string;
}

export interface SystemAlert {
  id: number;
  alert_type: string;
  slot_id?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  is_resolved: boolean;
  created_at: string;
}

export interface GateTapResult {
  status: 'ALLOWED' | 'REJECTED';
  action: 'OPEN_BARRIER' | 'KEEP_CLOSED';
  gate_id: string;
  message: string;
  session?: ParkingSession;
  reason?: string;
}
