/**
 * SensorValue — displays a sensor reading with label, formatted value, and unit.
 * Raw numbers are always accompanied by context.
 */
import React from 'react';

interface SensorValueProps {
  label: string;
  value: number | boolean | null | undefined;
  unit?: string;
  decimals?: number;
  mono?: boolean;
  status?: 'normal' | 'warning' | 'critical' | 'offline';
}

const STATUS_COLORS: Record<string, string> = {
  normal:   'var(--color-status-normal)',
  warning:  'var(--color-status-warning)',
  critical: 'var(--color-status-critical)',
  offline:  'var(--color-text-muted)',
};

export function SensorValue({ label, value, unit, decimals = 1, mono = true, status }: SensorValueProps) {
  const color = status ? STATUS_COLORS[status] : 'var(--color-text-primary)';

  let display: string;
  if (value === null || value === undefined) {
    display = '—';
  } else if (typeof value === 'boolean') {
    display = value ? 'Available' : 'Unavailable';
  } else {
    display = value.toFixed(decimals);
  }

  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: 'var(--space-2) 0' }}>
      <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>{label}</span>
      <span style={{
        fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)',
        fontSize: 'var(--text-sm)',
        fontWeight: 'var(--font-medium)',
        color,
        display: 'flex',
        alignItems: 'baseline',
        gap: 'var(--space-1)',
      }}>
        {display}
        {unit && value !== null && value !== undefined && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-sans)' }}>
            {unit}
          </span>
        )}
      </span>
    </div>
  );
}

/**
 * MetricTile — a prominent metric display for the dashboard overview.
 */
interface MetricTileProps {
  label: string;
  value: string | number | null;
  unit?: string;
  sub?: string;
  color?: string;
}

export function MetricTile({ label, value, unit, sub, color }: MetricTileProps) {
  const displayValue = value === null || value === undefined ? '—' : String(value);

  return (
    <div className="card" style={{ padding: 'var(--space-5)' }}>
      <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-2)', fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-1)' }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-2xl)',
          fontWeight: 'var(--font-semibold)',
          color: color ?? 'var(--color-text-primary)',
          lineHeight: 1,
        }}>
          {displayValue}
        </span>
        {unit && (
          <span style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-sans)' }}>
            {unit}
          </span>
        )}
      </div>
      {sub && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
          {sub}
        </div>
      )}
    </div>
  );
}
