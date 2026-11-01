import React, { useState, useEffect, useRef } from 'react';
import {
  ParkingSlot,
  SystemStats,
  RFIDCard,
  ParkingSession,
  SystemAlert,
} from './types';
import { api, WS_BASE } from './services/api';
import { StatsOverview } from './components/StatsOverview';
import { ParkingSlotCard } from './components/ParkingSlotCard';
import { BarrierIndicator } from './components/BarrierIndicator';
import { RfidControlPanel } from './components/RfidControlPanel';
import { CameraFeedViewer } from './components/CameraFeedViewer';
import { SimulationControls } from './components/SimulationControls';
import { ActiveSessionsTable } from './components/ActiveSessionsTable';
import { AlertsList } from './components/AlertsList';
import { Activity, Cpu, Camera, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [slots, setSlots] = useState<ParkingSlot[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [cards, setCards] = useState<RFIDCard[]>([]);
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);

  const loadData = async () => {
    try {
      const [slotsData, statsData, cardsData, sessionsData, alertsData] = await Promise.all([
        api.getSlots(),
        api.getStats(),
        api.getCards(),
        api.getActiveSessions(),
        api.getAlerts(),
      ]);
      setSlots(slotsData.slots);
      setStats(statsData);
      setCards(cardsData);
      setSessions(sessionsData);
      setAlerts(alertsData);
    } catch (err) {
      console.error('Failed to load initial data from backend:', err);
    }
  };

  useEffect(() => {
    loadData();

    // WebSocket Realtime connection
    const connectWs = () => {
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        console.log('[WS] Connected to live event stream');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.event_type === 'SLOT_UPDATE') {
            setSlots((prev) =>
              prev.map((s) => (s.slot_id === msg.data.slot_id ? { ...s, ...msg.data } : s))
            );
            api.getStats().then(setStats);
          } else if (msg.event_type === 'SLOTS_BULK_UPDATE' || msg.event_type === 'VISION_BULK_UPDATE') {
            loadData();
          } else if (msg.event_type === 'SESSION_CREATED' || msg.event_type === 'SESSION_COMPLETED') {
            api.getActiveSessions().then(setSessions);
            api.getStats().then(setStats);
            api.getAlerts().then(setAlerts);
          } else if (msg.event_type === 'MISMATCH_ALERT' || msg.event_type === 'ALERT') {
            loadData();
          } else if (msg.event_type === 'BARRIER_UPDATE' || msg.event_type === 'SAFETY_SENSOR_UPDATE') {
            api.getStats().then(setStats);
          } else if (msg.event_type === 'SYSTEM_RESET') {
            loadData();
          }
        } catch (e) {
          console.error('[WS Parse Error]', e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log('[WS] Disconnected. Reconnecting in 3s...');
        setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWs();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Handlers
  const handleToggleSlot = async (slot_id: string, current_occupied: boolean) => {
    await api.simulatorToggleSlot(slot_id, !current_occupied);
    loadData();
  };

  const handleInjectMismatch = async (slot_id: string) => {
    // Inject mismatch: Sensor reports true, Camera reports false
    await api.simulatorInjectMismatch(slot_id, true, false);
    loadData();
  };

  const handleFillAll = async () => {
    for (const s of slots) {
      await api.simulatorToggleSlot(s.slot_id, true);
    }
    loadData();
  };

  const handleClearAll = async () => {
    for (const s of slots) {
      await api.simulatorToggleSlot(s.slot_id, false);
    }
    loadData();
  };

  const handleInjectRandomMismatch = async () => {
    const target = slots[Math.floor(Math.random() * slots.length)]?.slot_id || 'P01';
    await handleInjectMismatch(target);
  };

  const handleReset = async () => {
    await api.simulatorReset();
    loadData();
  };

  const handleTapGate = async (card_uid: string, gate_id: 'ENTRY' | 'EXIT') => {
    const res = await api.tapGate(card_uid, gate_id);
    loadData();
    return res;
  };

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '1.5rem 1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Navigation & Status Bar */}
      <header
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          paddingBottom: '1rem',
          borderBottom: '1px solid #1e293b',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#f8fafc' }}>
              SMART PARKING SYSTEM
            </h1>
            <span className="badge badge-sim">
              {stats?.system_mode || 'SIMULATION'} MODE
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            ESP32 (HAL) &bull; RFID RC522 &bull; Ultrasonic Sensors &bull; OpenCV Camera AI &bull; FastAPI Realtime
          </p>
        </div>

        {/* System Health Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.65rem',
              background: '#0f172a',
              borderRadius: 8,
              border: '1px solid #1e293b',
              fontSize: '0.75rem',
            }}
          >
            <Activity size={14} color={wsConnected ? '#10b981' : '#ef4444'} />
            <span style={{ fontWeight: 600, color: wsConnected ? '#34d399' : '#f87171' }}>
              {wsConnected ? 'WebSocket Live' : 'Reconnecting...'}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.65rem',
              background: '#0f172a',
              borderRadius: 8,
              border: '1px solid #1e293b',
              fontSize: '0.75rem',
              color: '#38bdf8',
            }}
          >
            <Cpu size={14} /> HAL: {stats?.system_mode || 'SIMULATION'}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.65rem',
              background: '#0f172a',
              borderRadius: 8,
              border: '1px solid #1e293b',
              fontSize: '0.75rem',
              color: '#c084fc',
            }}
          >
            <Camera size={14} /> Camera AI (4 ROI)
          </div>

          <button
            className="btn-secondary"
            onClick={loadData}
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            <RefreshCw size={13} /> Đồng bộ
          </button>
        </div>
      </header>

      {/* KPI Stats Overview */}
      <StatsOverview stats={stats} />

      {/* Main Parking Slots Visualization */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
            Sơ Đồ 4 Vị Trí Đỗ Xe (P01 &ndash; P04)
          </h2>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Nhấp nút &ldquo;Đỗ xe vào&rdquo; hoặc &ldquo;Rời ô&rdquo; để thay đổi trạng thái thời gian thực
          </span>
        </div>

        <div className="slots-grid">
          {slots.map((slot) => (
            <ParkingSlotCard
              key={slot.slot_id}
              slot={slot}
              onToggle={handleToggleSlot}
              onInjectMismatch={handleInjectMismatch}
            />
          ))}
        </div>
      </section>

      {/* Camera Live Feed & ROI Viewer */}
      <CameraFeedViewer />

      {/* Gates, Barriers & RFID Simulation */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        <BarrierIndicator
          entryState={stats?.barrier_entry_state || 'CLOSED'}
          exitState={stats?.barrier_exit_state || 'CLOSED'}
          entryAngle={stats?.barrier_entry_angle || 0}
          exitAngle={stats?.barrier_exit_angle || 0}
          entryObstruction={stats?.barrier_entry_obstruction || false}
          exitObstruction={stats?.barrier_exit_obstruction || false}
          onRefresh={loadData}
        />

        <RfidControlPanel
          cards={cards}
          onTap={handleTapGate}
          onRefreshCards={loadData}
        />
      </div>

      {/* Simulation Lab Control Center */}
      <SimulationControls
        onReset={handleReset}
        onFillAll={handleFillAll}
        onClearAll={handleClearAll}
        onInjectRandomMismatch={handleInjectRandomMismatch}
      />

      {/* Sessions & Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        <ActiveSessionsTable sessions={sessions} />
        <AlertsList alerts={alerts} />
      </div>

      {/* Footer */}
      <footer style={{ textAlign: 'center', padding: '1.5rem 0', color: '#64748b', fontSize: '0.8rem', borderTop: '1px solid #1e293b' }}>
        SMART PARKING SYSTEM &bull; Đồ Án Kỹ Thuật Điện Tử & Nhúng &bull; Chế độ Full Software Simulation Sẵn Sàng Chuyển Đổi Phần Cứng
      </footer>
    </div>
  );
};

export default App;
