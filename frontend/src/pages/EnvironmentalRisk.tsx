/**
 * Environmental Risk page — heat stress, excess moisture, and environmental risk conditions.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { ConditionCard } from '../components/ui/ConditionCard';
import { SensorChart } from '../components/charts/SensorChart';
import type { FieldConditionSummary } from '../types';

const FIELD_ID = 'field-north-01';

export default function EnvironmentalRisk() {
  const { data: condition } = useQuery<FieldConditionSummary>({
    queryKey: ['field-condition', FIELD_ID],
    queryFn: () => api.fields.condition(FIELD_ID),
    refetchInterval: 15000,
  });

  const { data: tempChart } = useQuery({
    queryKey: ['chart', FIELD_ID, 'air_temperature_c', 24],
    queryFn: () => api.fields.chartData(FIELD_ID, 'air_temperature_c', 24),
  });

  const { data: humidityChart } = useQuery({
    queryKey: ['chart', FIELD_ID, 'air_humidity_pct', 24],
    queryFn: () => api.fields.chartData(FIELD_ID, 'air_humidity_pct', 24),
  });

  const { data: leafChart } = useQuery({
    queryKey: ['chart', FIELD_ID, 'leaf_wetness_pct', 24],
    queryFn: () => api.fields.chartData(FIELD_ID, 'leaf_wetness_pct', 24),
  });

  const heatExplanation = condition?.heat_stress_level !== 'none'
    ? `Air temperature is ${condition?.air_temperature_c?.toFixed(1)}°C. ${condition?.air_humidity_pct && condition.air_humidity_pct < 40 ? `Combined with low humidity (${condition.air_humidity_pct.toFixed(0)}%), this significantly increases crop water demand.` : 'This may stress the crop canopy.'}`
    : 'Air temperature is within the acceptable range for the current crop.';

  const excessExplanation = condition?.excess_moisture_level !== 'none'
    ? `Soil moisture is above optimal levels (${condition?.soil_moisture_pct?.toFixed(1)}%).${condition?.leaf_wetness_pct && condition.leaf_wetness_pct > 60 ? ` Leaf wetness is also elevated (${condition.leaf_wetness_pct.toFixed(0)}%), which increases the risk of fungal conditions.` : ''} Avoid irrigation and check drainage.`
    : 'Soil and surface moisture are within normal ranges.';

  const diseaseContextNote = condition?.excess_moisture_level !== 'none' && condition?.heat_stress_level === 'none'
    ? 'High moisture combined with moderate temperatures creates conditions that may be favorable for fungal issues. Conduct a visual crop inspection.'
    : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 900 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Environmental Risk</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Environmental stress conditions derived from sensor data. These are sensor-based risk assessments,
          not diagnoses. Always combine with visual crop inspection.
        </p>
      </div>

      {condition && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Heat stress */}
          <ConditionCard
            title="Heat Stress"
            severity={condition.heat_stress_level}
            explanation={heatExplanation}
            recommendedAction={condition.heat_stress_level !== 'none'
              ? 'Ensure adequate soil moisture. Consider providing temporary shade if available.'
              : undefined}
            icon="🌡"
          />

          {/* Excess moisture */}
          <ConditionCard
            title="Excess Moisture"
            severity={condition.excess_moisture_level}
            explanation={excessExplanation}
            recommendedAction={condition.excess_moisture_level !== 'none'
              ? 'Check drainage channels. Delay irrigation. Inspect for waterlogging.'
              : undefined}
            icon="💧"
          />

          {/* Activity signal */}
          <ConditionCard
            title="Field Activity Signal"
            severity={condition.activity_signal === 'elevated' ? 'low' : 'none'}
            explanation={condition.activity_signal === 'elevated'
              ? 'The vibration sensor has detected elevated activity. This sensor measures mechanical vibration only — it does not identify the source. A physical field inspection is recommended.'
              : 'Vibration sensor readings are within normal range.'}
            recommendedAction={condition.activity_signal === 'elevated'
              ? 'Conduct a physical field inspection to identify the cause of elevated activity.'
              : undefined}
            icon="◉"
          />

          {/* Environmental disease risk context note */}
          {diseaseContextNote && (
            <div className="card" style={{ background: 'var(--color-status-info-bg)', borderColor: 'var(--color-status-info-border)' }}>
              <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--color-status-info)', marginBottom: 'var(--space-2)' }}>
                Environmental Context Note
              </div>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.6 }}>
                {diseaseContextNote}
              </p>
              <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}>
                Note: This is an environmental risk context based on sensor readings only.
                The system does not diagnose diseases. A trained agronomist or visual inspection is required to confirm any disease presence.
              </p>
            </div>
          )}
          
          {/* ML Model Prediction */}
          <MLRiskPredictionCard condition={condition} />
        </div>
      )}

      {/* Environmental charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 'var(--space-5)' }}>
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            AIR TEMPERATURE — 24H
          </div>
          <SensorChart data={tempChart?.points ?? []} color="#f59e0b" unit="°C" refMax={35} height={160} loading={!tempChart} />
        </div>
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            AIR HUMIDITY — 24H
          </div>
          <SensorChart data={humidityChart?.points ?? []} color="#60a5fa" unit="%" refMin={40} height={160} loading={!humidityChart} />
        </div>
        <div className="card" style={{ gridColumn: 'span 1' }}>
          <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            LEAF WETNESS — 24H
          </div>
          <SensorChart data={leafChart?.points ?? []} color="#a78bfa" unit="%" height={160} loading={!leafChart} />
        </div>
      </div>
    </div>
  );
}

function MLRiskPredictionCard({ condition }: { condition: FieldConditionSummary }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ml-env-risk', condition.air_temperature_c, condition.air_humidity_pct, condition.soil_moisture_pct],
    queryFn: () => api.ml.predictEnvRisk({
      crop_type: 'Wheat', // Default for now
      temp: condition.air_temperature_c ?? 25.0,
      hum: condition.air_humidity_pct ?? 50.0,
      sm: condition.soil_moisture_pct ?? 50.0,
      pressure: 1013.25, // Mock value as it's not in condition
      solar: 0.5,        // Mock value
      organic_gas: 150,  // Mock value
      pest_vib: condition.activity_signal === 'elevated' ? 500 : 50
    }),
    refetchInterval: 15000,
  });

  if (isLoading) return <div>Loading ML Prediction...</div>;
  if (error) return <div>Error loading ML Prediction</div>;
  if (!data || data.is_stub) return null;

  const getSeverityColor = (risk: string) => {
    switch(risk) {
      case 'Safe': return 'var(--color-status-success)';
      case 'Heat_Stress':
      case 'Drought_Risk': return 'var(--color-status-warning)';
      case 'Fungal_Risk':
      case 'Waterlogging':
      case 'Pest_Risk': return 'var(--color-status-critical)';
      default: return 'var(--color-text-secondary)';
    }
  };

  return (
    <div className="card" style={{ borderLeft: `4px solid ${getSeverityColor(data.prediction?.risk_level)}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 'var(--text-lg)', marginBottom: 'var(--space-1)' }}>
            AI Risk Prediction
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)' }}>
            Random Forest Model Analysis
          </div>
        </div>
        <div style={{ 
          background: getSeverityColor(data.prediction?.risk_level), 
          color: 'white',
          padding: '4px 12px',
          borderRadius: 16,
          fontWeight: 600,
          fontSize: 'var(--text-sm)'
        }}>
          {data.prediction?.risk_level?.replace('_', ' ')} ({(data.confidence * 100).toFixed(0)}%)
        </div>
      </div>
    </div>
  );
}
