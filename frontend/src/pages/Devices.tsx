/**
 * Devices page — shows all field devices with live connectivity status.
 * Farmers can immediately see which devices are online, stale, or offline.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { api } from '../api/client';
import { StatusBadge, StatusDot } from '../components/ui/StatusBadge';
import type { Device } from '../types';

export default function Devices() {
  const { data: rawDevices, isLoading } = useQuery<Device[]>({
    queryKey: ['devices'],
    queryFn: () => api.devices.list(),
    refetchInterval: 10000,
  });

  // Hide simulator devices — only show real hardware
  const devices = rawDevices?.filter(d => d.source_type !== 'simulator');

  const liveCount = devices?.filter(d => d.connectivity_status === 'live').length ?? 0;
  const offlineCount = devices?.filter(d => d.connectivity_status === 'offline').length ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 800 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Device Management</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Field devices and their connectivity status. Devices are classified as
          <strong style={{ color: 'var(--color-status-normal)' }}> Live</strong> (≤5 min),
          <strong style={{ color: 'var(--color-status-warning)' }}> Stale</strong> (5–15 min), or
          <strong style={{ color: 'var(--color-status-offline)' }}> Offline</strong> (&gt;15 min).
        </p>
      </div>

      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-4)' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--color-status-normal)', fontFamily: 'var(--font-mono)' }}>{liveCount}</div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 4 }}>LIVE</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>{devices?.length ?? '—'}</div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 4 }}>TOTAL</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: offlineCount > 0 ? 'var(--color-status-critical)' : 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{offlineCount}</div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 4 }}>OFFLINE</div>
        </div>
      </div>

      {/* Device list */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : !devices?.length ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)', color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-3)' }}>⬡</div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-base)' }}>No devices registered</div>
          <div style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>
            Devices register automatically when they publish their first telemetry reading.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {devices.map(device => <DeviceCard key={device.id} device={device} />)}
        </div>
      )}

      {/* HC-05 integration note */}
      <div className="card" style={{ borderColor: 'var(--color-status-info-border)', background: 'var(--color-status-info-bg)' }}>
        <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--color-status-info)', marginBottom: 'var(--space-2)' }}>
          🔌 Hardware Integration — HC-05 Arduino
        </div>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          Connect your Arduino board via USB. The backend auto-detects the port and starts reading sensor data immediately.
        </p>
        <code style={{
          display: 'block', marginTop: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)',
          background: 'var(--color-surface-2)', borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--color-brand)',
          wordBreak: 'break-all',
        }}>
          /dev/cu.usbmodem14101  (auto-detected)
        </code>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
          Set <code>HARDWARE_ENABLED=true</code> and <code>HARDWARE_SERIAL_PORT=/dev/cu.usbmodem14101</code> in your <code>.env</code> file.
          The device registers automatically when it sends its first reading.
        </p>
      </div>
    </div>
  );
}

function DeviceCard({ device }: { device: Device }) {
  const statusBorder = device.connectivity_status === 'live'
    ? 'var(--color-status-normal-border)'
    : device.connectivity_status === 'stale'
    ? 'var(--color-status-warning-border)'
    : 'var(--color-status-offline-border)';

  return (
    <div className="card" style={{ borderLeftWidth: 3, borderLeftColor: statusBorder, borderLeftStyle: 'solid' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <StatusDot status={device.connectivity_status} />
          <div>
            <div style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)' }}>
              {device.source_type === 'hc05' ? 'HC-05 Arduino Sensor' : device.device_identifier}
            </div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 2 }}>
              {device.source_type === 'hc05' ? 'USB Serial — HC-05' : `Source: ${device.source_type}`}
              {device.firmware_version ? ` · v${device.firmware_version}` : ''}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          {device.last_seen_at ? (
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>Last seen</div>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)' }}>
                {formatDistanceToNow(parseISO(device.last_seen_at))} ago
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>Never seen</div>
          )}
          <StatusBadge status={device.connectivity_status} />
        </div>
      </div>
    </div>
  );
}
