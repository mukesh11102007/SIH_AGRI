/**
 * StatusBadge — communicates condition severity visually.
 * Always uses icon + text + color (never color alone for accessibility).
 */
import React from 'react';
import type { Severity, IrrigationDecision, DeviceStatus, AlertSeverity } from '../../types';

interface StatusBadgeProps {
  status: string;
  label?: string;
  size?: 'sm' | 'md';
}

const BADGE_CONFIG: Record<string, { cls: string; icon: string; label: string }> = {
  // Irrigation
  NORMAL:                   { cls: 'badge-normal',   icon: '✓', label: 'Normal' },
  MONITOR:                  { cls: 'badge-monitor',  icon: '◎', label: 'Monitor' },
  IRRIGATION_RECOMMENDED:   { cls: 'badge-critical', icon: '⚠', label: 'Irrigate Now' },
  IRRIGATION_BLOCKED:       { cls: 'badge-warning',  icon: '⊘', label: 'Water Unavailable' },
  EXCESS_MOISTURE:          { cls: 'badge-info',     icon: '↑', label: 'Excess Moisture' },

  // Severity
  none:     { cls: 'badge-normal',   icon: '✓', label: 'Normal' },
  low:      { cls: 'badge-monitor',  icon: '◎', label: 'Low' },
  medium:   { cls: 'badge-warning',  icon: '!', label: 'Medium' },
  high:     { cls: 'badge-warning',  icon: '!!', label: 'High' },
  critical: { cls: 'badge-critical', icon: '⚠', label: 'Critical' },

  // Device
  live:       { cls: 'badge-normal',  icon: '●', label: 'Live' },
  stale:      { cls: 'badge-warning', icon: '◑', label: 'Stale' },
  offline:    { cls: 'badge-offline', icon: '○', label: 'Offline' },
  never_seen: { cls: 'badge-offline', icon: '—', label: 'Never Seen' },

  // Alert
  info:     { cls: 'badge-info',     icon: 'ℹ', label: 'Info' },
  warning:  { cls: 'badge-warning',  icon: '!', label: 'Warning' },
  critical_alert: { cls: 'badge-critical', icon: '⚠', label: 'Critical' },

  // Data source
  simulator: { cls: 'badge-info',    icon: '⟳', label: 'Simulation' },
  esp32:     { cls: 'badge-normal',  icon: '⬡', label: 'ESP32 Live' },
  no_data:   { cls: 'badge-offline', icon: '—', label: 'No Data' },

  // Generic
  available:   { cls: 'badge-normal',   icon: '✓', label: 'Available' },
  unavailable: { cls: 'badge-critical', icon: '✗', label: 'Unavailable' },
  unknown:     { cls: 'badge-offline',  icon: '?', label: 'Unknown' },
  elevated:    { cls: 'badge-warning',  icon: '↑', label: 'Elevated' },
  normal_signal: { cls: 'badge-normal', icon: '—', label: 'Normal' },
};

export function StatusBadge({ status, label, size = 'md' }: StatusBadgeProps) {
  const config = BADGE_CONFIG[status] ?? { cls: 'badge-offline', icon: '?', label: status };
  const displayLabel = label ?? config.label;

  return (
    <span className={`badge ${config.cls}`} style={size === 'sm' ? { fontSize: '0.6rem' } : {}}>
      <span aria-hidden="true">{config.icon}</span>
      {displayLabel}
    </span>
  );
}

interface StatusDotProps {
  status: DeviceStatus;
}

export function StatusDot({ status }: StatusDotProps) {
  const cls =
    status === 'live' ? 'status-dot-live' :
    status === 'stale' ? 'status-dot-stale' :
    status === 'offline' ? 'status-dot-offline' : 'status-dot-offline';

  return <span className={`status-dot ${cls}`} aria-label={`Device ${status}`} />;
}
