import React from 'react';
import { SystemStats } from '../types';
import { Car, CheckCircle2, AlertOctagon, Banknote } from 'lucide-react';

interface Props {
  stats: SystemStats | null;
}

export const StatsOverview: React.FC<Props> = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="dashboard-grid">
      {/* Chỗ trống */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#10b981',
            padding: '0.85rem',
            borderRadius: 12,
          }}
        >
          <CheckCircle2 size={28} />
        </div>
        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            Vị trí còn trống
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#34d399' }}>
            {stats.available_slots} <span style={{ fontSize: '0.9rem', color: '#64748b' }}>/ {stats.total_slots}</span>
          </div>
        </div>
      </div>

      {/* Đang đỗ */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.15)',
            color: '#3b82f6',
            padding: '0.85rem',
            borderRadius: 12,
          }}
        >
          <Car size={28} />
        </div>
        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            Xe đang gửi
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#60a5fa' }}>
            {stats.occupied_slots}
          </div>
        </div>
      </div>

      {/* Cảnh báo sai lệch */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.15)',
            color: '#f59e0b',
            padding: '0.85rem',
            borderRadius: 12,
          }}
        >
          <AlertOctagon size={28} />
        </div>
        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            Sai lệch (Mismatch)
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fbbf24' }}>
            {stats.mismatch_slots}
          </div>
        </div>
      </div>

      {/* Doanh thu */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            background: 'rgba(168, 85, 247, 0.15)',
            color: '#a855f7',
            padding: '0.85rem',
            borderRadius: 12,
          }}
        >
          <Banknote size={28} />
        </div>
        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            Tổng doanh thu
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#c084fc' }}>
            {stats.total_revenue_vnd.toLocaleString()} <span style={{ fontSize: '0.85rem' }}>đ</span>
          </div>
        </div>
      </div>
    </div>
  );
};
