/**
 * Farm Setup — manage farm, fields, and crops.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { StatusBadge } from '../components/ui/StatusBadge';
import type { Farm, Crop } from '../types';

const FARM_ID = 'farm-001';

export default function FarmSetup() {
  const { data: farm } = useQuery<Farm>({
    queryKey: ['farm', FARM_ID],
    queryFn: () => api.farms.get(FARM_ID),
  });

  const { data: crops } = useQuery<Crop[]>({
    queryKey: ['crops'],
    queryFn: () => api.crops.list(),
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 800 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Farm Setup</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Farm configuration, fields, and crop thresholds.
        </p>
      </div>

      {/* Farm info */}
      {farm && (
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            FARM DETAILS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <InfoRow label="Farm Name" value={farm.name} />
            <InfoRow label="Location" value={farm.location ?? '—'} />
            <InfoRow label="Timezone" value={farm.timezone} />
            <InfoRow label="Farm ID" value={farm.id} mono />
          </div>
        </div>
      )}

      {/* Fields */}
      {farm?.fields && (
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            FIELDS ({farm.fields.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {farm.fields.map(field => (
              <div key={field.id} className="card-sm" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{field.name}</div>
                  <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{field.id}</div>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
                  {field.crop && <StatusBadge status="normal" label={field.crop.name} />}
                  {field.growth_stage && <StatusBadge status="monitor" label={field.growth_stage} size="sm" />}
                  {field.area_m2 && <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>{field.area_m2.toLocaleString()} m²</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Crop thresholds */}
      {crops && (
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            CROP THRESHOLDS
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Crop</th>
                  <th>Moisture Min</th>
                  <th>Moisture Max</th>
                  <th>Moisture Critical</th>
                  <th>Temp Max</th>
                  <th>Heat Stress</th>
                </tr>
              </thead>
              <tbody>
                {crops.map(crop => (
                  <tr key={crop.id}>
                    <td style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>{crop.name}</td>
                    <td><code className="mono">{crop.optimal_moisture_min_pct}%</code></td>
                    <td><code className="mono">{crop.optimal_moisture_max_pct}%</code></td>
                    <td><code className="mono" style={{ color: 'var(--color-status-critical)' }}>{crop.critical_moisture_min_pct}%</code></td>
                    <td><code className="mono">{crop.optimal_temp_max_c}°C</code></td>
                    <td><code className="mono" style={{ color: 'var(--color-status-warning)' }}>{crop.heat_stress_c}°C</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-3)' }}>
            These thresholds configure the decision engine for crop-specific recommendations.
            Custom crops and thresholds can be added via the REST API.
          </p>
        </div>
      )}

      {/* API Access */}
      <div className="card">
        <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>
          API ACCESS
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {[
            { label: 'API Documentation', url: '/api/docs' },
            { label: 'OpenAPI Spec', url: '/api/openapi.json' },
            { label: 'ReDoc', url: '/api/redoc' },
          ].map(link => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: 'var(--space-3)', background: 'var(--color-surface-2)',
                borderRadius: 'var(--radius-md)', color: 'var(--color-brand)',
                fontSize: 'var(--text-sm)', fontWeight: 500,
              }}
            >
              {link.label}
              <span style={{ color: 'var(--color-text-muted)' }}>→</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>{label}</span>
      <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontFamily: mono ? 'var(--font-mono)' : 'inherit', fontWeight: 500 }}>
        {value}
      </span>
    </div>
  );
}
