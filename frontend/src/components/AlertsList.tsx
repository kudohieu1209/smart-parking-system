import React from 'react';
import { SystemAlert } from '../types';
import { AlertTriangle, Bell } from 'lucide-react';

interface Props {
  alerts: SystemAlert[];
}

export const AlertsList: React.FC<Props> = ({ alerts }) => {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Bell size={20} color="#f59e0b" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Nhật Ký Cảnh Báo Hệ Thống</h3>
        </div>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Gần nhất</span>
      </div>

      {alerts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '1.25rem', color: '#64748b', fontSize: '0.85rem' }}>
          Không có cảnh báo nào phát sinh. Hệ thống hoạt động bình thường.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
          {alerts.slice(0, 5).map((a) => (
            <div
              key={a.id}
              style={{
                fontSize: '0.75rem',
                padding: '0.5rem 0.75rem',
                borderRadius: 6,
                background: 'rgba(245, 158, 11, 0.08)',
                borderLeft: '3px solid #f59e0b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <AlertTriangle size={14} color="#f59e0b" style={{ flexShrink: 0 }} />
                <span>{a.message}</span>
              </div>
              <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
                {new Date(a.created_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
