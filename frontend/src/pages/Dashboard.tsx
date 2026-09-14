import React, { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { api } from '../api/client';
import { useRealtimeUpdates } from '../api/useRealtimeUpdates';
import { StatusBadge, StatusDot } from '../components/ui/StatusBadge';
import { ConditionCard } from '../components/ui/ConditionCard';
import { MetricTile, SensorValue } from '../components/ui/SensorValue';
import { FarmZoneMap } from '../components/ui/FarmZoneMap';
import type { Zone } from '../components/ui/FarmZoneMap';
import type { FieldConditionSummary, WebSocketMessage } from '../types';

const FARM_ID = 'farm-001';
const FIELD_ID = 'field-north-01';

const IRRIGATION_ACTIONS: Record<string, string | null> = {
  NORMAL: null,
  MONITOR: 'Check soil moisture again in 1–2 hours.',
  IRRIGATION_RECOMMENDED: 'Irrigate the field as soon as possible.',
  IRRIGATION_BLOCKED: 'Refill the water tank or check the supply line.',
  EXCESS_MOISTURE: 'Check drainage. Avoid any additional irrigation.',
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  
  // Interactive Farm Zones State
  const [zones, setZones] = useState<Zone[]>([
    { id: 'z1', x: 20, y: 20, width: 90, height: 90, crop: 'wheat' },
    { id: 'z2', x: 130, y: 20, width: 90, height: 90, crop: 'rice' },
    { id: 'z3', x: 20, y: 130, width: 90, height: 90, crop: 'green_gram' }
  ]);
  const [activeZoneId, setActiveZoneId] = useState<string | null>('z1');
  
  // Get active crop name
  const activeZone = zones.find(z => z.id === activeZoneId);
  const selectedCrop = activeZone ? activeZone.crop : 'wheat';

  const { data: summary, isLoading, error } = useQuery<FieldConditionSummary>({
    queryKey: ['field-condition', FIELD_ID],
    queryFn: () => api.fields.condition(FIELD_ID),
    refetchInterval: 30000,
  });

  const { data: alerts } = useQuery({
    queryKey: ['alerts-active', FARM_ID],
    queryFn: () => api.farms.alerts(FARM_ID, 'active'),
    refetchInterval: 30000,
  });

  // Real-time updates
  useRealtimeUpdates({
    farmId: FARM_ID,
    onMessage: useCallback((msg: WebSocketMessage) => {
      if (msg.event === 'sensor_update') {
        setLastUpdate(new Date().toISOString());
        queryClient.setQueryData(['field-condition', FIELD_ID], (old: any) => ({
          ...old,
          irrigation_status: msg.irrigation_status ?? old?.irrigation_status,
          irrigation_severity: msg.irrigation_severity ?? old?.irrigation_severity,
          air_temperature_c: msg.air_temperature_c ?? old?.air_temperature_c,
          air_humidity_pct: msg.air_humidity_pct ?? old?.air_humidity_pct,
          soil_moisture_pct: msg.soil_moisture_pct ?? old?.soil_moisture_pct,
        }));
        queryClient.invalidateQueries({ queryKey: ['alerts-active'] });
      }
    }, [queryClient]),
  });

  if (isLoading) return <DashboardSkeleton />;
  if (error) return <ErrorState message="Unable to load farm data. Check backend connection." />;
  if (!summary) return null;

  const irrigationSeverity = summary.irrigation_status === 'IRRIGATION_RECOMMENDED' ? 'critical'
    : summary.irrigation_status === 'IRRIGATION_BLOCKED' ? 'high'
    : summary.irrigation_status === 'MONITOR' ? 'medium'
    : summary.irrigation_status === 'EXCESS_MOISTURE' ? 'medium' : 'none';

  // AI Insights Generator
  const generateAIInsights = () => {
    if (alerts && alerts.filter(a => a.severity === 'critical').length > 0) {
      const alert = alerts.find(a => a.severity === 'critical');
      return `Critical Issue Detected: ${alert?.title}. I recommend that you ${alert?.recommended_action?.toLowerCase() || 'address this immediately'}.`;
    }
    
    // Check if backend provided rule-based advice
    if ((summary as any).ai_advice) {
      return (summary as any).ai_advice;
    }
    
    if (summary.irrigation_status !== 'NORMAL') {
      const reasoning = summary.irrigation_reasoning || 'Conditions are outside optimal bounds.';
      const action = IRRIGATION_ACTIONS[summary.irrigation_status] || '';
      return `Attention required for your ${selectedCrop.replace('_', ' ')} crop. ${reasoning} ${action}`.trim();
    }
    return `Your ${selectedCrop.replace('_', ' ')} field is in excellent condition! Soil moisture is optimal and no significant stress factors are detected. The ML models predict stable health for the next 24 hours.`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 'var(--content-max-w)' }}>

      {/* ── Page header ───────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-3xl)', marginBottom: 2, color: 'var(--color-brand)' }}>Farm Overview</h1>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <StatusDot status={summary.device_status} />
            <span>{summary.field_name}</span>
            {lastUpdate && (
              <span>· Updated {formatDistanceToNow(new Date(lastUpdate))} ago</span>
            )}
          </div>
        </div>
      </div>
      
      {/* ── Interactive Farm Zone Map ────────────────────────── */}
      <FarmZoneMap 
        zones={zones} 
        activeZoneId={activeZoneId} 
        onZonesChange={setZones} 
        onActiveZoneChange={setActiveZoneId} 
      />

      {/* ── Critical alerts banner ───────────────────────────── */}
      {alerts && alerts.filter(a => a.severity === 'critical').map(alert => (
        <div key={alert.id} className="alert-banner alert-banner-critical">
          <div>
            <div style={{ fontWeight: 'var(--font-semibold)', color: 'var(--color-status-critical)', marginBottom: 4, fontSize: 'var(--text-md)' }}>
              {alert.title}
            </div>
            <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)' }}>
              {alert.explanation}
            </div>
            {alert.recommended_action && (
              <div style={{ color: 'var(--color-status-critical)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)', fontWeight: 500 }}>
                Action: {alert.recommended_action}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* ── Key metrics Grid ────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
        <MetricTile
          label="Soil Moisture"
          value={summary.soil_moisture_pct?.toFixed(1) ?? null}
          unit="%"
          color={summary.water_stress_level !== 'none' ? 'var(--color-status-warning)' : 'var(--color-brand)'}
        />
        <MetricTile
          label="Air Temperature"
          value={summary.air_temperature_c?.toFixed(1) ?? null}
          unit="°C"
          color={summary.heat_stress_level !== 'none' ? 'var(--color-status-warning)' : 'var(--color-text-primary)'}
        />
        <MetricTile
          label="Air Humidity"
          value={summary.air_humidity_pct?.toFixed(0) ?? null}
          unit="%"
        />
        <MetricTile
          label="Water Source"
          value={summary.water_availability === 'available' ? 'OK' : 'Check'}
          color={summary.water_availability !== 'available' ? 'var(--color-status-critical)' : 'var(--color-status-normal)'}
        />
      </div>

      {/* ── Main Layout: 2 Columns ───────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 'var(--space-6)' }}>
        
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* AI Insights Panel */}
          <div className="card" style={{ background: 'linear-gradient(135deg, var(--color-surface-1) 0%, var(--color-brand-glow) 100%)', border: '1px solid var(--color-brand)', position: 'relative', overflow: 'hidden' }}>
            <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--font-bold)', color: 'var(--color-brand-dim)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              AI Crop Advisor
            </h2>
            <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-md)', lineHeight: 1.6, color: 'var(--color-text-primary)', fontWeight: 500 }}>
              {generateAIInsights()}
            </p>
          </div>

          {/* ML Prediction / Irrigation Status */}
          <ConditionCard
            title="ML Irrigation Prediction"
            severity={irrigationSeverity}
            explanation={summary.irrigation_reasoning}
            recommendedAction={IRRIGATION_ACTIONS[summary.irrigation_status] ?? undefined}
          />

          {/* Activity Signal (If active) */}
          {summary.activity_signal === 'elevated' && (
            <ConditionCard
              title="Field Activity Detected"
              severity="medium"
              explanation="Elevated vibration detected in the field. This could be equipment, animals, or human activity."
              recommendedAction="Verify field security if unprompted."
              compact
            />
          )}
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Detailed Readings */}
          <div className="card">
            <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 'var(--font-semibold)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Detailed Readings
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <SensorValue label="Soil Temperature" value={summary.soil_temperature_c} unit="°C" />
              <div className="divider" style={{ margin: 'var(--space-1) 0' }} />
              <SensorValue label="Light Intensity" value={summary.light_lux} unit="lux" decimals={0} />
              <div className="divider" style={{ margin: 'var(--space-1) 0' }} />
              <SensorValue label="Leaf Wetness" value={summary.leaf_wetness_pct} unit="%" />
            </div>
            {summary.last_updated && (
              <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-4)' }}>
                Data source: {summary.data_source}
              </div>
            )}
          </div>

          {/* Devices & History Snapshot */}
          <div className="card">
            <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 'var(--font-semibold)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              System Status
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-2) 0' }}>
              <span style={{ color: 'var(--color-text-primary)' }}>Primary Edge Device</span>
              <StatusBadge status={summary.device_status} />
            </div>
            <div className="divider" style={{ margin: 'var(--space-2) 0' }} />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-2) 0' }}>
              <span style={{ color: 'var(--color-text-primary)' }}>ML Inference Engine</span>
              <StatusBadge status="live" />
            </div>
            <div className="divider" style={{ margin: 'var(--space-2) 0' }} />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-2) 0' }}>
              <span style={{ color: 'var(--color-text-primary)' }}>Network Connectivity</span>
              <span className="badge badge-normal">99.9% Uptime</span>
            </div>
          </div>

          {/* Scenario control (demo panel) */}
          <ScenarioControl />
        </div>
      </div>
    </div>
  );
}

function ScenarioControl() {
  const [active, setActive] = useState('NORMAL');
  const [changing, setChanging] = useState(false);
  const queryClient = useQueryClient();

  const SCENARIOS = [
    { id: 'NORMAL', label: 'Normal' },
    { id: 'WATER_STRESS', label: 'Water Stress' },
    { id: 'HEAT_STRESS', label: 'Heat Stress' },
    { id: 'EXCESS_MOISTURE', label: 'Excess Moisture' },
    { id: 'LOW_WATER', label: 'Low Water' },
    { id: 'ACTIVITY_EVENT', label: 'Activity Event' },
  ];

  const apply = async (scenario: string) => {
    setChanging(true);
    await api.simulator.setScenario(scenario);
    setActive(scenario);
    setChanging(false);
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['field-condition'] });
    }, 12000); // Wait for next reading
  };

  return (
    <div className="card" style={{ borderColor: 'var(--color-status-info-border)', background: 'var(--color-status-info-bg)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
        <span style={{ color: 'var(--color-status-info)', fontSize: 'var(--text-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          DEMO — SIMULATION CONTROL
        </span>
      </div>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-3)', lineHeight: 1.5 }}>
        Switch scenarios to test the decision engine. The frontend has no knowledge of the scenario — only raw sensor values flow through.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        {SCENARIOS.map(s => (
          <button
            key={s.id}
            className={`btn ${active === s.id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => apply(s.id)}
            disabled={changing}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div className="skeleton" style={{ height: 60, width: '100%' }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-4)' }}>
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-6)' }}>
         <div className="skeleton" style={{ height: 300 }} />
         <div className="skeleton" style={{ height: 300 }} />
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="alert-banner alert-banner-critical" style={{ maxWidth: 500 }}>
      <span>⚠</span>
      <div>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Connection Error</div>
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>{message}</div>
      </div>
    </div>
  );
}
