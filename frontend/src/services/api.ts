import {
  SlotListResponse,
  SystemStats,
  RFIDCard,
  ParkingSession,
  SystemAlert,
  GateTapResult
} from '../types';

export const API_BASE = 'http://localhost:8000/api/v1';
export const WS_BASE = 'ws://localhost:8000/ws/live';
export const LIVE_FEED_URL = `${API_BASE}/vision/live-feed`;

export const api = {
  async getSlots(): Promise<SlotListResponse> {
    const res = await fetch(`${API_BASE}/slots`);
    if (!res.ok) throw new Error('Failed to fetch slots');
    return res.json();
  },

  async getStats(): Promise<SystemStats> {
    const res = await fetch(`${API_BASE}/system/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
  },

  async getCards(): Promise<RFIDCard[]> {
    const res = await fetch(`${API_BASE}/cards`);
    if (!res.ok) throw new Error('Failed to fetch cards');
    return res.json();
  },

  async toggleCardActive(card_uid: string, is_active: boolean): Promise<RFIDCard> {
    const res = await fetch(`${API_BASE}/cards/toggle-active`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_uid, is_active }),
    });
    if (!res.ok) throw new Error('Failed to toggle card active status');
    return res.json();
  },

  async getActiveSessions(): Promise<ParkingSession[]> {
    const res = await fetch(`${API_BASE}/sessions/active`);
    if (!res.ok) throw new Error('Failed to fetch active sessions');
    return res.json();
  },

  async getAlerts(): Promise<SystemAlert[]> {
    const res = await fetch(`${API_BASE}/system/alerts`);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  },

  async tapGate(card_uid: string, gate_id: 'ENTRY' | 'EXIT'): Promise<GateTapResult> {
    const endpoint = gate_id === 'ENTRY' ? '/gate/entry-tap' : '/gate/exit-tap';
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_uid, gate_id }),
    });
    return res.json();
  },

  async commandBarrier(gate_id: 'ENTRY' | 'EXIT', command: 'OPEN' | 'CLOSE'): Promise<any> {
    const res = await fetch(`${API_BASE}/gate/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gate_id, command }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Barrier command failed');
    }
    return res.json();
  },

  async setSafetySensor(gate_id: 'ENTRY' | 'EXIT', has_obstruction: boolean): Promise<any> {
    const res = await fetch(`${API_BASE}/gate/safety-sensor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gate_id, has_obstruction }),
    });
    return res.json();
  },

  async simulatorToggleSlot(slot_id: string, occupied: boolean): Promise<any> {
    const res = await fetch(`${API_BASE}/simulator/slot-toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot_id, occupied }),
    });
    return res.json();
  },

  async simulatorInjectMismatch(slot_id: string, sensor_occupied: boolean, camera_occupied: boolean): Promise<any> {
    const res = await fetch(`${API_BASE}/simulator/inject-mismatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot_id, sensor_occupied, camera_occupied }),
    });
    return res.json();
  },

  async simulatorReset(): Promise<any> {
    const res = await fetch(`${API_BASE}/simulator/reset`, {
      method: 'POST',
    });
    return res.json();
  },

  async setSystemMode(mode: 'SIMULATION' | 'HARDWARE'): Promise<any> {
    const res = await fetch(`${API_BASE}/system/mode?mode=${mode}`, {
      method: 'POST',
    });
    return res.json();
  },
};

