/**
 * History — time-series charts for all sensors over configurable time windows.
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { SensorChart } from '../components/charts/SensorChart';
import type { ChartData } from '../types';

const FIELD_ID = 'field-north-01';

const SENSORS: Array<{ key: string; label: string; unit: string; color: string; refMin?: number; refMax?: number }> = [
  { key: 'soil_moisture_pct',  label: 'Soil Moisture',    unit: '%',  color: '#22c55e', refMin: 20, refMax: 70 },
  { key: 'air_temperature_c',  label: 'Air Temperature',  unit: '°C', color: '#f59e0b', refMax: 35 },
  { key: 'air_humidity_pct',   label: 'Air Humidity',     unit: '%',  color: '#60a5fa' },
  { key: 'soil_temperature_c', label: 'Soil Temperature', unit: '°C', color: '#fb923c' },
  { key: 'light_lux',          label: 'Light Intensity',  unit: 'lux', color: '#facc15' },
  { key: 'leaf_wetness_pct',   label: 'Leaf Wetness',     unit: '%',  color: '#a78bfa' },
];

const TIME_RANGES = [
  { label: '6h',  hours: 6 },
  { label: '24h', hours: 24 },
  { label: '48h', hours: 48 },
  { label: '7d',  hours: 168 },
];

export default function History() {
  const [selectedHours, setSelectedHours] = useState(24);
  const [activeSensor, setActiveSensor] = useState<string | null>(null);

  const displaySensors = activeSensor ? SENSORS.filter(s => s.key === activeSensor) : SENSORS;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 'var(--content-max-w)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 2 }}>Historical Data</h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
            Sensor trends and patterns over time
          </p>
        </div>

        {/* Time range selector */}
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {TIME_RANGES.map(r => (
            <button
              key={r.hours}
              className={`btn btn-sm ${selectedHours === r.hours ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedHours(r.hours)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sensor filter */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <button
          className={`btn btn-sm ${activeSensor === null ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setActiveSensor(null)}
        >
          All Sensors
        </button>
        {SENSORS.map(s => (
          <button
            key={s.key}
            className={`btn btn-sm ${activeSensor === s.key ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveSensor(s.key === activeSensor ? null : s.key)}
            style={activeSensor === s.key ? {} : { borderLeft: `3px solid ${s.color}` }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {displaySensors.map(sensor => (
          <SensorChartPanel
            key={`${sensor.key}-${selectedHours}`}
            fieldId={FIELD_ID}
            sensor={sensor}
            hours={selectedHours}
          />
        ))}
      </div>
    </div>
  );
}

function SensorChartPanel({
  fieldId, sensor, hours,
}: {
  fieldId: string;
  sensor: typeof SENSORS[0];
  hours: number;
}) {
  const { data, isLoading } = useQuery<ChartData>({
    queryKey: ['chart', fieldId, sensor.key, hours],
    queryFn: () => api.fields.chartData(fieldId, sensor.key, hours),
    staleTime: 60000,
  });

  const min = data?.points.length ? Math.min(...data.points.map(p => p.v)) : null;
  const max = data?.points.length ? Math.max(...data.points.map(p => p.v)) : null;
  const avg = data?.points.length
    ? data.points.reduce((s, p) => s + p.v, 0) / data.points.length
    : null;

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ width: 3, height: 16, background: sensor.color, borderRadius: 2, flexShrink: 0 }} />
          <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-base)' }}>
            {sensor.label}
          </span>
        </div>
        {!isLoading && data && (
          <div style={{ display: 'flex', gap: 'var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}>
            <span>Min: <strong style={{ color: 'var(--color-text-secondary)' }}>{min?.toFixed(1)} {sensor.unit}</strong></span>
            <span>Avg: <strong style={{ color: 'var(--color-text-secondary)' }}>{avg?.toFixed(1)} {sensor.unit}</strong></span>
            <span>Max: <strong style={{ color: 'var(--color-text-secondary)' }}>{max?.toFixed(1)} {sensor.unit}</strong></span>
          </div>
        )}
      </div>

      <SensorChart
        data={data?.points ?? []}
        color={sensor.color}
        unit={sensor.unit}
        refMin={sensor.refMin}
        refMax={sensor.refMax}
        height={180}
        loading={isLoading}
      />

      {sensor.refMin !== undefined || sensor.refMax !== undefined ? (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)', display: 'flex', gap: 'var(--space-3)' }}>
          {sensor.refMin !== undefined && <span>— Min threshold: {sensor.refMin}{sensor.unit}</span>}
          {sensor.refMax !== undefined && <span>— Max threshold: {sensor.refMax}{sensor.unit}</span>}
        </div>
      ) : null}
    </div>
  );
}
