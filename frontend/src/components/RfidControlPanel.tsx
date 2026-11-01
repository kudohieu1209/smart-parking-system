import React, { useState } from 'react';
import { RFIDCard, GateTapResult } from '../types';
import { CreditCard, LogIn, LogOut, CheckCircle, XCircle, Lock, Unlock, HelpCircle } from 'lucide-react';
import { api } from '../services/api';

interface Props {
  cards: RFIDCard[];
  onTap: (card_uid: string, gate_id: 'ENTRY' | 'EXIT') => Promise<GateTapResult>;
  onRefreshCards?: () => void;
}

export const RfidControlPanel: React.FC<Props> = ({ cards, onTap, onRefreshCards }) => {
  const [selectedCard, setSelectedCard] = useState<string>(cards[0]?.card_uid || 'RFID-DEMO-01');
  const [lastResult, setLastResult] = useState<GateTapResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const currentCardObj = cards.find((c) => c.card_uid === selectedCard);

  const handleTap = async (gate_id: 'ENTRY' | 'EXIT', customUid?: string) => {
    setIsLoading(true);
    try {
      const uidToTap = customUid || selectedCard;
      const result = await onTap(uidToTap, gate_id);
      setLastResult(result);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleCardLock = async () => {
    if (!currentCardObj) return;
    setIsLoading(true);
    try {
      await api.toggleCardActive(currentCardObj.card_uid, !currentCardObj.is_active);
      if (onRefreshCards) onRefreshCards();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CreditCard size={20} color="#a78bfa" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Mô phỏng Quẹt Thẻ RFID (RC522)</h3>
        </div>
        <span className="badge badge-sim">SPI PROTOCOL</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <label style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>
              Chọn Thẻ RFID:
            </label>
            {currentCardObj && (
              <span style={{ fontSize: '0.75rem', color: currentCardObj.is_active ? '#34d399' : '#f87171', fontWeight: 700 }}>
                {currentCardObj.is_active ? '● Đang kích hoạt' : '● ĐÃ BỊ KHÓA'}
              </span>
            )}
          </div>

          <select
            value={selectedCard}
            onChange={(e) => setSelectedCard(e.target.value)}
            style={{
              width: '100%',
              background: '#0f172a',
              border: `1px solid ${currentCardObj?.is_active === false ? '#ef4444' : '#334155'}`,
              color: '#f8fafc',
              padding: '0.65rem',
              borderRadius: 8,
              fontSize: '0.85rem',
              outline: 'none',
            }}
          >
            {cards.map((c) => (
              <option key={c.card_uid} value={c.card_uid}>
                {c.card_uid} — {c.owner_name} ({c.vehicle_plate}) [{c.is_active ? 'ACTIVE' : 'LOCKED'}]
              </option>
            ))}
          </select>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
          <button
            className="btn-primary"
            onClick={() => handleTap('ENTRY')}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.4rem',
              background: '#0284c7',
              fontSize: '0.8rem',
            }}
          >
            <LogIn size={15} /> Quét Vào Cổng
          </button>

          <button
            className="btn-primary"
            onClick={() => handleTap('EXIT')}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.4rem',
              background: '#7c3aed',
              fontSize: '0.8rem',
            }}
          >
            <LogOut size={15} /> Quét Ra Cổng
          </button>
        </div>

        {/* Special Test Actions */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem', paddingTop: '0.25rem' }}>
          <button
            className="btn-secondary"
            onClick={() => handleTap('ENTRY', 'RFID-UNKNOWN-99')}
            disabled={isLoading}
            title="Thử quẹt thẻ chưa đăng ký trong cơ sở dữ liệu"
            style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
          >
            <HelpCircle size={14} color="#f59e0b" /> Quét Thẻ Lạ
          </button>

          <button
            className="btn-secondary"
            onClick={handleToggleCardLock}
            disabled={isLoading || !currentCardObj}
            title="Khóa hoặc mở khóa thẻ đang chọn để kiểm thử từ chối thẻ"
            style={{
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.35rem',
              color: currentCardObj?.is_active ? '#fca5a5' : '#86efac',
            }}
          >
            {currentCardObj?.is_active ? <Lock size={14} /> : <Unlock size={14} />}
            {currentCardObj?.is_active ? 'Khóa Thẻ Này' : 'Mở Khóa Thẻ'}
          </button>
        </div>

        {/* Live Feedback Banner */}
        {lastResult && (
          <div
            style={{
              marginTop: '0.35rem',
              padding: '0.75rem',
              borderRadius: 8,
              background: lastResult.status === 'ALLOWED' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
              border: `1px solid ${lastResult.status === 'ALLOWED' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.6rem',
            }}
          >
            {lastResult.status === 'ALLOWED' ? (
              <CheckCircle size={20} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
            ) : (
              <XCircle size={20} color="#f87171" style={{ flexShrink: 0, marginTop: 2 }} />
            )}
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: lastResult.status === 'ALLOWED' ? '#34d399' : '#f87171' }}>
                {lastResult.status === 'ALLOWED' ? 'CHO PHÉP MỞ CỔNG' : 'TỪ CHỐI QUA CỔNG'} [{lastResult.reason || 'ALLOWED'}]
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
                {lastResult.message}
              </div>
              {lastResult.session && (
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.3rem' }} className="font-mono">
                  Phiên #{lastResult.session.id} &bull; Biển số: {lastResult.session.vehicle_plate || 'N/A'} &bull; Cước: {lastResult.session.fee_amount.toLocaleString()} đ
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
