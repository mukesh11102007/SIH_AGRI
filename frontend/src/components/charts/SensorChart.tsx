/**
 * SensorChart — time-series line chart for historical sensor data.
 * Uses Recharts — meaningful visualization with proper labels and tooltips.
 */
import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { ChartPoint } from '../../types';

interface SensorChartProps {
  data: ChartPoint[];
  color?: string;
  unit?: string;
  label?: string;
  refMin?: number;
  refMax?: number;
  height?: number;
  loading?: boolean;
}

function CustomTooltip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--color-surface-2)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: '8px 12px',
      fontSize: 'var(--text-xs)',
    }}>
      <div style={{ color: 'var(--color-text-muted)', marginBottom: 2 }}>
        {payload[0]?.payload?.t ? format(parseISO(payload[0].payload.t), 'MMM d, HH:mm') : label}
      </div>
      <div style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
        {payload[0].value?.toFixed(1)} {unit ?? ''}
      </div>
    </div>
  );
}

export function SensorChart({
  data, color = '#22c55e', unit, label, refMin, refMax, height = 200, loading,
}: SensorChartProps) {
  if (loading) {
    return (
      <div className="skeleton" style={{ height, borderRadius: 'var(--radius-md)' }} />
    );
  }

  if (!data.length) {
    return (
      <div style={{
        height, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)',
        color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)',
      }}>
        No data available
      </div>
    );
  }

  const formattedData = data.map(p => ({
    t: p.t,
    v: p.v,
    label: format(parseISO(p.t), 'HH:mm'),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={formattedData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}${unit ? '' : ''}`}
        />
        {refMin !== undefined && (
          <ReferenceLine y={refMin} stroke="var(--color-status-warning)" strokeDasharray="4 4" />
        )}
        {refMax !== undefined && (
          <ReferenceLine y={refMax} stroke="var(--color-status-warning)" strokeDasharray="4 4" />
        )}
        <Tooltip content={<CustomTooltip unit={unit} />} />
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={2}
          fill={`url(#grad-${color.replace('#', '')})`}
          dot={false}
          activeDot={{ r: 4, fill: color, stroke: 'var(--color-bg)', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
