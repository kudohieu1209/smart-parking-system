import React, { useState } from 'react';
import { Camera, Eye, EyeOff, Video, Sparkles, RefreshCw } from 'lucide-react';
import { LIVE_FEED_URL, API_BASE } from '../services/api';

export const CameraFeedViewer: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [snapshotKey, setSnapshotKey] = useState<number>(Date.now());
  const [useSnapshot, setUseSnapshot] = useState<boolean>(false);

  const handleRefreshSnapshot = () => {
    setSnapshotKey(Date.now());
    setUseSnapshot(true);
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Camera size={20} color="#c084fc" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>
            Camera AI Simulator (Live Stream & Vùng ROI)
          </h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="badge badge-sim">640x480 &bull; 4 ROI</span>
          <button
            className="btn-secondary"
            onClick={() => setIsPlaying(!isPlaying)}
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            {isPlaying ? <EyeOff size={14} /> : <Eye size={14} />}
            {isPlaying ? 'Tắt Stream' : 'Bật Stream'}
          </button>
        </div>
      </div>

      {/* Video Container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxHeight: '380px',
          background: '#030712',
          borderRadius: 10,
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #1e293b',
        }}
      >
        {isPlaying ? (
          <img
            key={useSnapshot ? snapshotKey : 'live'}
            src={useSnapshot ? `${API_BASE}/vision/frame?t=${snapshotKey}` : LIVE_FEED_URL}
            alt="Simulated Parking Camera Stream"
            style={{ width: '100%', height: 'auto', display: 'block', objectFit: 'contain' }}
            onError={(e) => {
              // Fallback placeholder if stream is loading
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        ) : (
          <div style={{ padding: '3.5rem 1rem', textAlign: 'center', color: '#64748b' }}>
            <Video size={48} style={{ margin: '0 auto 0.75rem auto', opacity: 0.5 }} />
            <p style={{ fontSize: '0.85rem' }}>Luồng Camera đang tạm dừng.</p>
            <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Bấm &ldquo;Bật Stream&rdquo; để xem luồng khung hình mô phỏng thời gian thực.
            </p>
          </div>
        )}

        {/* Live Indicator Overlay */}
        {isPlaying && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 10,
              background: 'rgba(0, 0, 0, 0.65)',
              backdropFilter: 'blur(4px)',
              padding: '0.25rem 0.6rem',
              borderRadius: 6,
              fontSize: '0.7rem',
              fontWeight: 700,
              color: '#34d399',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            LIVE FEED &bull; OPENCV ROI DETECTOR
          </div>
        )}
      </div>

      {/* Footer Details */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          marginTop: '0.75rem',
          fontSize: '0.75rem',
          color: '#94a3b8',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <Sparkles size={14} color="#fbbf24" />
          <span>Thuật toán: Baseline Canny Edge & Standard Deviation trên 4 ROI</span>
        </div>

        <button
          className="btn-secondary"
          onClick={handleRefreshSnapshot}
          style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
        >
          <RefreshCw size={12} /> Chụp Snapshot
        </button>
      </div>
    </div>
  );
};
