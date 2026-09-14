/**
 * Irrigation page — detailed irrigation recommendation with full reasoning.
 */
import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { api } from '../api/client';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ConditionCard } from '../components/ui/ConditionCard';
import { SensorChart } from '../components/charts/SensorChart';
import { useRealtimeUpdates } from '../api/useRealtimeUpdates';
import type { FieldConditionSummary, Recommendation, WebSocketMessage } from '../types';

const FARM_ID = 'farm-001';
const FIELD_ID = 'field-north-01';

export default function Irrigation() {
  const queryClient = useQueryClient();
  const { data: condition } = useQuery<FieldConditionSummary>({
    queryKey: ['field-condition', FIELD_ID],
    queryFn: () => api.fields.condition(FIELD_ID),
    refetchInterval: 15000,
  });

  useRealtimeUpdates({
    farmId: FARM_ID,
    onMessage: (msg: WebSocketMessage) => {
      if (msg.event === 'sensor_update') {
        queryClient.setQueryData(['field-condition', FIELD_ID], (old: any) => ({
          ...old,
          irrigation_status: msg.irrigation_status ?? old?.irrigation_status,
          irrigation_severity: msg.irrigation_severity ?? old?.irrigation_severity,
          air_temperature_c: msg.air_temperature_c ?? old?.air_temperature_c,
          air_humidity_pct: msg.air_humidity_pct ?? old?.air_humidity_pct,
          soil_moisture_pct: msg.soil_moisture_pct ?? old?.soil_moisture_pct,
        }));
      }
    },
  });

  const { data: currentRec } = useQuery<Recommendation | null>({
    queryKey: ['current-rec', FIELD_ID],
    queryFn: () => api.fields.currentRecommendation(FIELD_ID),
    refetchInterval: 15000,
  });

  const { data: chartData } = useQuery({
    queryKey: ['chart', FIELD_ID, 'soil_moisture_pct', 24],
    queryFn: () => api.fields.chartData(FIELD_ID, 'soil_moisture_pct', 24),
  });

  const irrigationSeverity = condition?.irrigation_status === 'IRRIGATION_RECOMMENDED' ? 'critical'
    : condition?.irrigation_status === 'IRRIGATION_BLOCKED' ? 'high'
    : condition?.irrigation_status === 'MONITOR' ? 'medium'
    : condition?.irrigation_status === 'EXCESS_MOISTURE' ? 'medium' : 'none';

  const actions: Record<string, string> = {
    NORMAL: 'No action needed at this time.',
    MONITOR: 'Check soil moisture again in 1–2 hours. Prepare for possible irrigation.',
    IRRIGATION_RECOMMENDED: 'Irrigate the field as soon as possible to prevent crop stress.',
    IRRIGATION_BLOCKED: 'Refill the water tank or check supply line before irrigating.',
    EXCESS_MOISTURE: 'Do not irrigate. Check drainage to prevent waterlogging.',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 900 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Irrigation</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Multi-factor irrigation analysis based on soil moisture, temperature, humidity, leaf wetness, and water availability.
        </p>
      </div>

      {/* Primary recommendation */}
      {condition && (
        <ConditionCard
          title="Current Irrigation Status"
          severity={irrigationSeverity}
          explanation={condition.irrigation_reasoning}
          recommendedAction={actions[condition.irrigation_status]}
          icon="💧"
        />
      )}

      {/* Key contributing factors */}
      {condition && (
        <div className="card">
          <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            CONTRIBUTING FACTORS
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
            <FactorTile label="Soil Moisture" value={condition.soil_moisture_pct} unit="%" threshold="40–70%" />
            <FactorTile label="Air Temperature" value={condition.air_temperature_c} unit="°C" threshold="< 35°C" />
            <FactorTile label="Humidity" value={condition.air_humidity_pct} unit="%" threshold="> 40%" />
            <FactorTile label="Leaf Wetness" value={condition.leaf_wetness_pct} unit="%" />
            <div className="card-sm" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>Water Source</div>
              <StatusBadge
                status={condition.water_availability === 'available' ? 'available'
                  : condition.water_availability === 'unavailable' ? 'unavailable' : 'unknown'}
              />
            </div>
          </div>
        </div>
      )}

      {/* Soil moisture chart */}
      <div className="card">
        <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
          SOIL MOISTURE — LAST 24 HOURS
        </h2>
        <SensorChart
          data={chartData?.points ?? []}
          color="#22c55e"
          unit="%"
          refMin={20}
          refMax={70}
          height={200}
          loading={!chartData}
        />
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}>
          Dashed lines indicate critical minimum (20%) and optimal maximum (70%) thresholds.
        </div>
      </div>

      {/* Recent recommendations */}
      {currentRec && (
        <div className="card">
          <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>
            LATEST RECOMMENDATION
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
            <StatusBadge status={currentRec.severity} />
            <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
              Generated by {currentRec.generated_by.replace('_', ' ')}
              {currentRec.confidence_pct ? ` · ${currentRec.confidence_pct}% confidence` : ''}
              {' · '}{formatDistanceToNow(parseISO(currentRec.created_at))} ago
            </span>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.6 }}>
            {currentRec.reasoning}
          </div>
        </div>
      )}
    </div>
  );
}

function FactorTile({ label, value, unit, threshold }: {
  label: string; value: number | null | undefined; unit: string; threshold?: string;
}) {
  return (
    <div className="card-sm">
      <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--text-lg)', color: 'var(--color-text-primary)' }}>
        {value?.toFixed(1) ?? '—'}<span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginLeft: 2 }}>{unit}</span>
      </div>
      {threshold && <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 4 }}>Optimal: {threshold}</div>}
    </div>
  );
}
