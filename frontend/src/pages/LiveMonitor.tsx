/**
 * Live Monitor — real-time sensor readings updated via WebSocket.
 * Shows all sensor values as readable data, not raw ADC counts.
 */
import React, { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { api } from '../api/client';
import { useRealtimeUpdates } from '../api/useRealtimeUpdates';
import { StatusBadge, StatusDot } from '../components/ui/StatusBadge';
import { SensorValue } from '../components/ui/SensorValue';
import type { SensorReading, FieldConditionSummary, WebSocketMessage } from '../types';

const FARM_ID = 'farm-001';
const FIELD_ID = 'field-north-01';

interface LiveTick {
  timestamp: string;
  source: string;
  irrigation_status?: string;
}

export default function LiveMonitor() {
  const queryClient = useQueryClient();
  const [liveTicks, setLiveTicks] = useState<LiveTick[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const { data: latest, isLoading } = useQuery<SensorReading | null>({
    queryKey: ['latest-reading', FIELD_ID],
    queryFn: () => api.fields.latestReading(FIELD_ID),
    refetchInterval: 15000,
  });

  const { data: condition } = useQuery<FieldConditionSummary>({
    queryKey: ['field-condition', FIELD_ID],
    queryFn: () => api.fields.condition(FIELD_ID),
    refetchInterval: 15000,
  });

  useRealtimeUpdates({
    farmId: FARM_ID,
    onMessage: useCallback((msg: WebSocketMessage) => {
      if (msg.event === 'sensor_update') {
        setWsConnected(true);
        setLiveTicks(prev => [
          { timestamp: msg.server_timestamp, source: msg.source ?? 'unknown', irrigation_status: msg.irrigation_status },
          ...prev.slice(0, 9),
        ]);
        
        // Optimistically update the cache with live WebSocket data since DB is not available yet
        queryClient.setQueryData(['latest-reading', FIELD_ID], (old: any) => ({
          ...old,
          air_temperature_c: msg.air_temperature_c ?? old?.air_temperature_c,
          air_humidity_pct: msg.air_humidity_pct ?? old?.air_humidity_pct,
          soil_moisture_pct: msg.soil_moisture_pct ?? old?.soil_moisture_pct,
          water_level_available: msg.water_level_available ?? old?.water_level_available,
          source: msg.source ?? old?.source,
          received_at: msg.server_timestamp,
        }));
        
        queryClient.setQueryData(['field-condition', FIELD_ID], (old: any) => ({
          ...old,
          irrigation_status: msg.irrigation_status ?? old?.irrigation_status,
          irrigation_severity: msg.irrigation_severity ?? old?.irrigation_severity,
          air_temperature_c: msg.air_temperature_c ?? old?.air_temperature_c,
          air_humidity_pct: msg.air_humidity_pct ?? old?.air_humidity_pct,
          soil_moisture_pct: msg.soil_moisture_pct ?? old?.soil_moisture_pct,
        }));
      }
    }, [queryClient]),
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Live Monitor</h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
            Real-time sensor readings from the field device.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <StatusDot status={wsConnected ? 'live' : 'stale'} />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            {wsConnected ? 'WebSocket active' : 'Connecting…'}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-5)' }}>
        {/* Atmospheric */}
        <div className="card">
          <SectionTitle icon="🌡" title="Atmospheric" />
          {isLoading ? <ReadingsSkeleton /> : (
            <>
              <SensorValue label="Air Temperature" value={latest?.air_temperature_c} unit="°C"
                status={condition?.heat_stress_level !== 'none' ? 'warning' : 'normal'} />
              <Divider />
              <SensorValue label="Air Humidity" value={latest?.air_humidity_pct} unit="%" />
              <Divider />
              <SensorValue label="Light Intensity" value={latest?.light_lux} unit="lux" decimals={0} />
            </>
          )}
        </div>

        {/* Soil */}
        <div className="card">
          <SectionTitle icon="🌱" title="Soil" />
          {isLoading ? <ReadingsSkeleton /> : (
            <>
              <SensorValue label="Soil Moisture" value={latest?.soil_moisture_pct} unit="%"
                status={condition?.water_stress_level !== 'none' ? 'warning' : 'normal'} />
              <Divider />
              <SensorValue label="Soil Temperature" value={latest?.soil_temperature_c} unit="°C" />
            </>
          )}
        </div>

        {/* Surface & Environment */}
        <div className="card">
          <SectionTitle icon="🍃" title="Surface & Environment" />
          {isLoading ? <ReadingsSkeleton /> : (
            <>
              <SensorValue label="Leaf Wetness" value={latest?.leaf_wetness_pct} unit="%" />
              <Divider />
              <SensorValue
                label="Water Source"
                value={latest?.water_level_available}
                status={latest?.water_level_available === false ? 'critical' : 'normal'}
              />
            </>
          )}
        </div>

        {/* Activity signal */}
        <div className="card">
          <SectionTitle icon="◉" title="Activity Signal" />
          {isLoading ? <ReadingsSkeleton /> : (
            <>
              <SensorValue label="Vibration (raw ADC)" value={latest?.vibration_raw} unit="" decimals={0} />
              <Divider />
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5, marginTop: 'var(--space-2)' }}>
                The vibration sensor provides a raw activity signal.
                It does not identify specific pests or causes.
                Elevated readings warrant a physical inspection.
              </div>
            </>
          )}
        </div>
      </div>

      {/* Reading metadata */}
      {latest && (
        <div className="card-sm" style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'center' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>Source: </span>
            <StatusBadge status={latest.source} label={latest.source === 'simulator' ? 'Simulation' : `ESP32 — ${latest.source}`} size="sm" />
          </div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
            Received: {latest.received_at ? formatDistanceToNow(parseISO(latest.received_at)) + ' ago' : '—'}
          </div>
          {latest.validation_flags && Object.keys(latest.validation_flags).length > 0 && (
            <div>
              <span className="badge badge-warning">Validation flags: {Object.keys(latest.validation_flags).join(', ')}</span>
            </div>
          )}
        </div>
      )}

      {/* Live activity log */}
      {liveTicks.length > 0 && (
        <div className="card">
          <div style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>
            RECENT READINGS
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {liveTicks.map((tick, i) => (
              <div key={tick.timestamp} style={{
                display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
                padding: 'var(--space-1) 0', opacity: i === 0 ? 1 : 0.5 + (0.5 * (1 - i / liveTicks.length)),
                fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)',
                borderBottom: i < liveTicks.length - 1 ? '1px solid var(--color-border)' : 'none',
              }}>
                <span style={{ color: 'var(--color-brand)', flexShrink: 0 }}>✓</span>
                <span style={{ color: 'var(--color-text-muted)' }}>
                  {new Date(tick.timestamp).toLocaleTimeString()}
                </span>
                <span style={{ color: 'var(--color-text-secondary)' }}>{tick.source}</span>
                {tick.irrigation_status && (
                  <StatusBadge status={tick.irrigation_status} size="sm" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: string; title: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
      <span>{icon}</span>
      <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</span>
    </div>
  );
}

function Divider() {
  return <div className="divider" style={{ margin: 'var(--space-1) 0' }} />;
}

function ReadingsSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {[...Array(2)].map((_, i) => <div key={i} className="skeleton" style={{ height: 20 }} />)}
    </div>
  );
}
