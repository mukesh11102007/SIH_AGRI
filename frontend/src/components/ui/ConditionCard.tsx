/**
 * ConditionCard — the primary insight unit.
 * Shows condition name, severity, brief explanation, and recommended action.
 * This is what farmers see instead of raw sensor values.
 */
import React from 'react';
import type { Severity } from '../../types';
import { StatusBadge } from './StatusBadge';

interface ConditionCardProps {
  title: string;
  severity: Severity | string;
  explanation: string;
  recommendedAction?: string | null;
  icon?: string;
  compact?: boolean;
}

const SEVERITY_STYLES: Record<string, { border: string; accent: string }> = {
  none:     { border: 'var(--color-status-normal-border)',   accent: 'var(--color-status-normal)' },
  low:      { border: 'var(--color-status-monitor-border)',  accent: 'var(--color-status-monitor)' },
  medium:   { border: 'var(--color-status-warning-border)',  accent: 'var(--color-status-warning)' },
  high:     { border: 'var(--color-status-warning-border)',  accent: 'var(--color-status-warning)' },
  critical: { border: 'var(--color-status-critical-border)', accent: 'var(--color-status-critical)' },
};

export function ConditionCard({
  title, severity, explanation, recommendedAction, icon, compact = false,
}: ConditionCardProps) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.none;

  return (
    <div
      className="card"
      style={{
        borderLeftWidth: 3,
        borderLeftColor: style.border,
        borderLeftStyle: 'solid',
        padding: compact ? 'var(--space-4)' : 'var(--space-5)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {icon && <span style={{ fontSize: '1.2em', color: style.accent }}>{icon}</span>}
          <span style={{ fontWeight: 'var(--font-semibold)', color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)' }}>
            {title}
          </span>
        </div>
        <StatusBadge status={severity} size="sm" />
      </div>

      <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.55, marginBottom: recommendedAction ? 'var(--space-3)' : 0 }}>
        {explanation}
      </p>

      {recommendedAction && (
        <div style={{
          background: 'var(--color-surface-2)',
          borderRadius: 'var(--radius-sm)',
          padding: 'var(--space-2) var(--space-3)',
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-secondary)',
          borderLeft: `2px solid ${style.accent}`,
        }}>
          <span style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', fontSize: '0.65rem', fontWeight: 600, letterSpacing: '0.06em', display: 'block', marginBottom: 2 }}>
            Recommended Action
          </span>
          {recommendedAction}
        </div>
      )}
    </div>
  );
}
