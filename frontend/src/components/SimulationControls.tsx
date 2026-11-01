import React from 'react';
import { RotateCcw, AlertTriangle, Play, Sparkles } from 'lucide-react';

interface Props {
  onReset: () => void;
  onFillAll: () => void;
  onClearAll: () => void;
  onInjectRandomMismatch: () => void;
}

export const SimulationControls: React.FC<Props> = ({
  onReset,
  onFillAll,
  onClearAll,
  onInjectRandomMismatch,
}) => {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={20} color="#fbbf24" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Bảng Điều Khiển Mô Phỏng (Lab Simulator)</h3>
        </div>
        <span className="badge badge-sim">MOCK ACTIVE</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.65rem' }}>
        <button
          className="btn-secondary"
          onClick={onFillAll}
          style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}
        >
          <Play size={14} color="#38bdf8" /> Lấp đầy 4 ô
        </button>

        <button
          className="btn-secondary"
          onClick={onClearAll}
          style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}
        >
          <RotateCcw size={14} color="#34d399" /> Làm trống 4 ô
        </button>

        <button
          className="btn-secondary"
          onClick={onInjectRandomMismatch}
          style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem', borderColor: 'rgba(245, 158, 11, 0.4)' }}
        >
          <AlertTriangle size={14} color="#fbbf24" /> Tạo lỗi Mismatch
        </button>

        <button
          className="btn-secondary"
          onClick={onReset}
          style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}
        >
          <RotateCcw size={14} color="#ef4444" /> Đặt lại hệ thống
        </button>
      </div>
    </div>
  );
};
