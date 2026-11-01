import React from 'react';
import { ParkingSession } from '../types';
import { Clock, Shield } from 'lucide-react';

interface Props {
  sessions: ParkingSession[];
}

export const ActiveSessionsTable: React.FC<Props> = ({ sessions }) => {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Clock size={20} color="#38bdf8" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Danh Sách Xe Đang Gửi ({sessions.length})</h3>
        </div>
        <span className="badge badge-online">ACTIVE</span>
      </div>

      {sessions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b', fontSize: '0.85rem' }}>
          Hiện tại không có phương tiện nào đang đỗ trong bãi.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                <th style={{ padding: '0.5rem' }}>ID</th>
                <th style={{ padding: '0.5rem' }}>Mã Thẻ</th>
                <th style={{ padding: '0.5rem' }}>Biển Số</th>
                <th style={{ padding: '0.5rem' }}>Giờ Vào</th>
                <th style={{ padding: '0.5rem' }}>Trạng Thái</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <td style={{ padding: '0.5rem', fontWeight: 600 }}>#{s.id}</td>
                  <td style={{ padding: '0.5rem' }} className="font-mono">{s.card_uid}</td>
                  <td style={{ padding: '0.5rem', color: '#38bdf8', fontWeight: 700 }}>{s.vehicle_plate || 'Chưa nhận diện'}</td>
                  <td style={{ padding: '0.5rem', color: '#94a3b8' }}>
                    {new Date(s.entry_time).toLocaleTimeString()}
                  </td>
                  <td style={{ padding: '0.5rem' }}>
                    <span className="badge badge-online">{s.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
