import React from 'react';
import { ParkingSlot } from '../types';
import { Car, AlertTriangle, CheckCircle, Radio, Camera } from 'lucide-react';

interface Props {
  slot: ParkingSlot;
  onToggle: (slot_id: string, current_occupied: boolean) => void;
  onInjectMismatch: (slot_id: string) => void;
}

export const ParkingSlotCard: React.FC<Props> = ({ slot, onToggle, onInjectMismatch }) => {
  const isOccupied = slot.status === 'OCCUPIED';
  const isMismatch = slot.status === 'MISMATCH';
  const isEmpty = slot.status === 'EMPTY';

  return (
    <div className={`parking-slot-card status-${slot.status}`}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '0.05em' }}>
            {slot.slot_id}
          </span>
          {isMismatch && (
            <span style={{ display: 'inline-flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.75rem', fontWeight: 700 }}>
              <AlertTriangle size={14} style={{ marginRight: 2 }} /> MISMATCH
            </span>
          )}
        </div>

        <span
          className={`badge ${
            isEmpty ? 'badge-online' : isOccupied ? 'badge-offline' : 'badge-sim'
          }`}
        >
          {slot.status}
        </span>
      </div>

      {/* Visual Car Graphic / Empty Space Indicator */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem 0',
          background: 'rgba(0, 0, 0, 0.25)',
          borderRadius: 8,
          margin: '0.75rem 0',
          position: 'relative',
        }}
      >
        {isOccupied && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#f87171' }}>
            <Car size={48} strokeWidth={1.8} />
            <span style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.25rem', color: '#fca5a5' }}>
              Đang có xe đỗ
            </span>
          </div>
        )}

        {isEmpty && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#34d399' }}>
            <CheckCircle size={44} strokeWidth={1.8} />
            <span style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.25rem', color: '#6ee7b7' }}>
              Vị trí sẵn sàng
            </span>
          </div>
        )}

        {isMismatch && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#fbbf24' }}>
            <AlertTriangle size={48} strokeWidth={2} />
            <span style={{ fontSize: '0.8rem', fontWeight: 700, marginTop: '0.25rem', color: '#fde68a' }}>
              Sai lệch cảm biến & AI
            </span>
          </div>
        )}
      </div>

      {/* Sensor & Vision Telemetry Details */}
      <div
        style={{
          fontSize: '0.75rem',
          color: '#94a3b8',
          background: 'rgba(255, 255, 255, 0.03)',
          padding: '0.6rem',
          borderRadius: 6,
          marginBottom: '0.75rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.35rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <Radio size={12} color="#60a5fa" /> Siêu âm HC-SR04:
          </span>
          <span className="font-mono" style={{ fontWeight: 600, color: '#f1f5f9' }}>
            {slot.sensor_distance_cm.toFixed(1)} cm ({slot.sensor_occupied ? 'Có vật thể' : 'Trống'})
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <Camera size={12} color="#c084fc" /> Camera AI (OpenCV):
          </span>
          <span className="font-mono" style={{ fontWeight: 600, color: '#f1f5f9' }}>
            {slot.camera_occupied ? 'Xe đỗ' : 'Trống'} ({Math.round(slot.camera_confidence * 100)}%)
          </span>
        </div>
      </div>

      {/* Simulator Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        <button
          className={isOccupied ? 'btn-danger' : 'btn-success'}
          onClick={() => onToggle(slot.slot_id, isOccupied)}
          style={{ width: '100%', fontSize: '0.75rem' }}
        >
          {isOccupied ? 'Rời ô đỗ' : 'Đỗ xe vào'}
        </button>

        <button
          className="btn-secondary"
          onClick={() => onInjectMismatch(slot.slot_id)}
          title="Tạo lỗi không khớp giữa Camera và Siêu âm"
          style={{ width: '100%', fontSize: '0.75rem' }}
        >
          Lỗi Mismatch
        </button>
      </div>
    </div>
  );
};
