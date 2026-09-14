/**
 * API client — all HTTP calls to the backend go through here.
 * Base URL is handled by Vite's dev proxy; in production, set VITE_API_BASE_URL.
 */
import type {
  Farm, Field, Crop, Device, SensorReading, FieldConditionSummary,
  Alert, Recommendation, AnalyticsSummary, ChartData,
} from '../types';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Farms ─────────────────────────────────────────────────────────────────
export const api = {
  farms: {
    list: () => request<Farm[]>('/farms'),
    get: (id: string) => request<Farm>(`/farms/${id}`),
    create: (body: Partial<Farm>) => request<Farm>('/farms', { method: 'POST', body: JSON.stringify(body) }),
    dashboard: (farmId: string) => request<FieldConditionSummary[]>(`/farms/${farmId}/dashboard`),
    alerts: (farmId: string, status = 'active') =>
      request<Alert[]>(`/farms/${farmId}/alerts?status=${status}`),
  },

  fields: {
    list: (farmId: string) => request<Field[]>(`/farms/${farmId}/fields`),
    get: (fieldId: string) => request<Field>(`/fields/${fieldId}`),
    create: (body: Partial<Field>) =>
      request<Field>('/fields', { method: 'POST', body: JSON.stringify(body) }),
    update: (fieldId: string, body: Partial<Field>) =>
      request<Field>(`/fields/${fieldId}`, { method: 'PATCH', body: JSON.stringify(body) }),
    condition: (fieldId: string) =>
      request<FieldConditionSummary>(`/fields/${fieldId}/condition`),
    latestReading: (fieldId: string) =>
      request<SensorReading | null>(`/fields/${fieldId}/readings/latest`),
    readings: (fieldId: string, hours = 24) =>
      request<SensorReading[]>(`/fields/${fieldId}/readings?hours=${hours}`),
    alerts: (fieldId: string, status?: string) =>
      request<Alert[]>(`/fields/${fieldId}/alerts${status ? `?status=${status}` : ''}`),
    recommendations: (fieldId: string) =>
      request<Recommendation[]>(`/fields/${fieldId}/recommendations`),
    currentRecommendation: (fieldId: string) =>
      request<Recommendation | null>(`/fields/${fieldId}/recommendations/current`),
    analytics: (fieldId: string, hours = 24) =>
      request<AnalyticsSummary>(`/fields/${fieldId}/analytics/summary?hours=${hours}`),
    chartData: (fieldId: string, sensor: string, hours = 24) =>
      request<ChartData>(`/fields/${fieldId}/analytics/chart?sensor=${sensor}&hours=${hours}`),
  },

  ml: {
    predictEnvRisk: (body: any) => request<any>('/predict/env-risk', { method: 'POST', body: JSON.stringify(body) })
  },

  crops: {
    list: () => request<Crop[]>('/crops'),
  },

  devices: {
    list: () => request<Device[]>('/devices'),
    forField: (fieldId: string) => request<Device[]>(`/fields/${fieldId}/devices`),
  },

  alerts: {
    acknowledge: (alertId: string) =>
      request<Alert>(`/alerts/${alertId}/acknowledge`, { method: 'POST' }),
    resolve: (alertId: string) =>
      request<Alert>(`/alerts/${alertId}/resolve`, { method: 'POST' }),
  },

  simulator: {
    getScenario: () => request<{ scenario: string; device_target: string | null }>('/simulator/scenario'),
    setScenario: (scenario: string) =>
      request<{ scenario: string; applied_to: string; message: string }>(
        '/simulator/scenario',
        { method: 'POST', body: JSON.stringify({ scenario }) }
      ),
  },

  health: () => request<{ status: string; version: string }>('/health'),
};
