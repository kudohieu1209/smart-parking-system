import React, { useState } from 'react';
import { DoorOpen, AlertOctagon, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';

interface Props {
  entryState: 'OPEN' | 'CLOSED';
  exitState: 'OPEN' | 'CLOSED';
  entryAngle?: number;
  exitAngle?: number;
  entryObstruction?: boolean;
  exitObstruction?: boolean;
  onRefresh?: () => void;
}

export const BarrierIndicator: React.FC<Props> = ({
  entryState,
  exitState,
  entryAngle = 0,
  exitAngle = 0,
  entryObstruction = false,
  exitObstruction = false,
  onRefresh,
}) => {
  const [loadingGate, setLoadingGate] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleCommand = async (gate: 'ENTRY' | 'EXIT', command: 'OPEN' | 'CLOSE') => {
    setLoadingGate(gate);
    setErrorMessage(null);
    try {
      await api.commandBarrier(gate, command);
      if (onRefresh) onRefresh();
    } catch (e: any) {
      setErrorMessage(`[Cảnh báo an toàn] ${e.message}`);
    } finally {
      setLoadingGate(null);
    }
  };

  const handleToggleObstruction = async (gate: 'ENTRY' | 'EXIT', current: boolean) => {
    setLoadingGate(gate);
    setErrorMessage(null);
    try {
      await api.setSafetySensor(gate, !current);
      if (onRefresh) onRefresh();
    } finally {
      setLoadingGate(null);
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <DoorOpen size={20} color="#38bdf8" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Kiểm soát Barrier Servo & Cảm Biến An Toàn</h3>
        </div>
        <span className="badge badge-sim">KHÓA LIÊN ĐỘNG AN TOÀN</span>
      </div>

      {errorMessage && (
        <div
          style={{
            padding: '0.65rem 0.85rem',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: 8,
            fontSize: '0.8rem',
            color: '#f87171',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <ShieldAlert size={18} style={{ flexShrink: 0 }} />
          <span>{errorMessage}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        {/* Entry Barrier */}
        <div
          style={{
            background: '#0f172a',
            border: `1px solid ${entryState === 'OPEN' ? '#34d399' : '#334155'}`,
            borderRadius: 10,
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#94a3b8' }}>
              CỔNG VÀO (ENTRY GATE)
            </span>
            <span
              className={`badge ${
                entryState === 'OPEN' ? 'badge-online' : 'badge-offline'
              }`}
            >
              {entryState} ({entryAngle}°)
            </span>
          </div>

          {/* Visual Barrier Bar Graphic */}
          <div
            style={{
              height: '8px',
              background: '#1e293b',
              borderRadius: '4px',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                width: `${(entryAngle / 90) * 100}%`,
                height: '100%',
                background: entryState === 'OPEN' ? '#10b981' : '#ef4444',
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          {/* Safety Sensor Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.5rem',
              background: entryObstruction ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.08)',
              borderRadius: 6,
              border: `1px solid ${entryObstruction ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.2)'}`,
              fontSize: '0.75rem',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              {entryObstruction ? (
                <AlertOctagon size={14} color="#f87171" />
              ) : (
                <CheckCircle2 size={14} color="#34d399" />
              )}
              Cảm biến IR:
            </span>
            <span style={{ fontWeight: 700, color: entryObstruction ? '#f87171' : '#34d399' }}>
              {entryObstruction ? 'CÓ VẬT CẢN (NGUY HIỂM)' : 'THÔNG THOÁNG (CLEAR)'}
            </span>
          </div>

          {/* Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <button
              className="btn-success"
              onClick={() => handleCommand('ENTRY', 'OPEN')}
              disabled={loadingGate === 'ENTRY'}
              style={{ fontSize: '0.75rem', padding: '0.4rem' }}
            >
              Mở Barrier (90°)
            </button>
            <button
              className="btn-danger"
              onClick={() => handleCommand('ENTRY', 'CLOSE')}
              disabled={loadingGate === 'ENTRY'}
              style={{ fontSize: '0.75rem', padding: '0.4rem' }}
            >
              Hạ Barrier (0°)
            </button>
          </div>

          <button
            className="btn-secondary"
            onClick={() => handleToggleObstruction('ENTRY', entryObstruction)}
            style={{ fontSize: '0.75rem', padding: '0.35rem', borderColor: entryObstruction ? '#f87171' : '#374151' }}
          >
            {entryObstruction ? 'Gỡ bỏ vật cản' : 'Mô phỏng vật cản dưới barrier'}
          </button>
        </div>

        {/* Exit Barrier */}
        <div
          style={{
            background: '#0f172a',
            border: `1px solid ${exitState === 'OPEN' ? '#34d399' : '#334155'}`,
            borderRadius: 10,
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#94a3b8' }}>
              CỔNG RA (EXIT GATE)
            </span>
            <span
              className={`badge ${
                exitState === 'OPEN' ? 'badge-online' : 'badge-offline'
              }`}
            >
              {exitState} ({exitAngle}°)
            </span>
          </div>

          {/* Visual Barrier Bar Graphic */}
          <div
            style={{
              height: '8px',
              background: '#1e293b',
              borderRadius: '4px',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                width: `${(exitAngle / 90) * 100}%`,
                height: '100%',
                background: exitState === 'OPEN' ? '#10b981' : '#ef4444',
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          {/* Safety Sensor Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.5rem',
              background: exitObstruction ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.08)',
              borderRadius: 6,
              border: `1px solid ${exitObstruction ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.2)'}`,
              fontSize: '0.75rem',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              {exitObstruction ? (
                <AlertOctagon size={14} color="#f87171" />
              ) : (
                <CheckCircle2 size={14} color="#34d399" />
              )}
              Cảm biến IR:
            </span>
            <span style={{ fontWeight: 700, color: exitObstruction ? '#f87171' : '#34d399' }}>
              {exitObstruction ? 'CÓ VẬT CẢN (NGUY HIỂM)' : 'THÔNG THOÁNG (CLEAR)'}
            </span>
          </div>

          {/* Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <button
              className="btn-success"
              onClick={() => handleCommand('EXIT', 'OPEN')}
              disabled={loadingGate === 'EXIT'}
              style={{ fontSize: '0.75rem', padding: '0.4rem' }}
            >
              Mở Barrier (90°)
            </button>
            <button
              className="btn-danger"
              onClick={() => handleCommand('EXIT', 'CLOSE')}
              disabled={loadingGate === 'EXIT'}
              style={{ fontSize: '0.75rem', padding: '0.4rem' }}
            >
              Hạ Barrier (0°)
            </button>
          </div>

          <button
            className="btn-secondary"
            onClick={() => handleToggleObstruction('EXIT', exitObstruction)}
            style={{ fontSize: '0.75rem', padding: '0.35rem', borderColor: exitObstruction ? '#f87171' : '#374151' }}
          >
            {exitObstruction ? 'Gỡ bỏ vật cản' : 'Mô phỏng vật cản dưới barrier'}
          </button>
        </div>
      </div>
    </div>
  );
};
