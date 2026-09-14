/**
 * TypeScript types mirroring the backend Pydantic schemas.
 * Single source of truth for all API data shapes in the frontend.
 */

export type Severity = 'none' | 'low' | 'medium' | 'high' | 'critical';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'expired';
export type DeviceStatus = 'live' | 'stale' | 'offline' | 'never_seen';
export type DataSource = 'simulator' | 'esp32' | 'esp32-cam-node' | 'no_data';

export type IrrigationDecision =
  | 'NORMAL'
  | 'MONITOR'
  | 'IRRIGATION_RECOMMENDED'
  | 'IRRIGATION_BLOCKED'
  | 'EXCESS_MOISTURE';

export interface Crop {
  id: string;
  name: string;
  variety: string | null;
  optimal_moisture_min_pct: number;
  optimal_moisture_max_pct: number;
  critical_moisture_min_pct: number;
  optimal_temp_min_c: number;
  optimal_temp_max_c: number;
  heat_stress_c: number;
  created_at: string;
}

export interface Field {
  id: string;
  farm_id: string;
  crop_id: string | null;
  name: string;
  area_m2: number | null;
  growth_stage: string | null;
  created_at: string;
  updated_at: string;
  crop: Crop | null;
}

export interface Farm {
  id: string;
  name: string;
  location: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
  fields?: Field[];
}

export interface Device {
  id: string;
  field_id: string;
  device_identifier: string;
  source_type: string;
  firmware_version: string | null;
  last_seen_at: string | null;
  is_active: boolean;
  connectivity_status: DeviceStatus;
  created_at: string;
}

export interface SensorReading {
  id: string;
  device_id: string;
  field_id: string;
  received_at: string;
  device_timestamp: string | null;
  source: string;
  air_temperature_c: number | null;
  air_humidity_pct: number | null;
  soil_moisture_pct: number | null;
  soil_temperature_c: number | null;
  light_lux: number | null;
  leaf_wetness_pct: number | null;
  vibration_raw: number | null;
  water_level_available: boolean | null;
  is_validated: boolean;
  validation_flags: Record<string, string> | null;
}

export interface FieldConditionSummary {
  field_id: string;
  field_name: string;
  crop_name: string | null;
  growth_stage: string | null;
  data_source: DataSource;
  last_updated: string | null;

  // Sensor values
  air_temperature_c: number | null;
  air_humidity_pct: number | null;
  soil_moisture_pct: number | null;
  soil_temperature_c: number | null;
  light_lux: number | null;
  leaf_wetness_pct: number | null;
  water_level_available: boolean | null;

  // Conditions
  irrigation_status: IrrigationDecision;
  irrigation_severity: Severity;
  irrigation_reasoning: string;
  water_stress_level: Severity;
  heat_stress_level: Severity;
  excess_moisture_level: Severity;
  water_availability: 'available' | 'low' | 'unavailable' | 'unknown';
  activity_signal: 'normal' | 'elevated';

  active_alert_count: number;
  device_status: DeviceStatus;
}

export interface Alert {
  id: string;
  field_id: string;
  device_id: string | null;
  alert_type: string;
  severity: AlertSeverity;
  title: string;
  explanation: string;
  recommended_action: string | null;
  contributing_factors: Record<string, unknown> | null;
  status: AlertStatus;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface Recommendation {
  id: string;
  field_id: string;
  recommendation_type: string;
  decision: string;
  severity: Severity;
  reasoning: string;
  contributing_factors: Record<string, unknown> | null;
  generated_by: string;
  confidence_pct: number | null;
  created_at: string;
}

export interface AnalyticsSummary {
  field_id: string;
  period_hours: number;
  reading_count: number;
  temperature: { avg_c: number | null; min_c: number | null; max_c: number | null };
  humidity: { avg_pct: number | null };
  soil_moisture: { avg_pct: number | null; min_pct: number | null; max_pct: number | null };
  light: { avg_lux: number | null; max_lux: number | null };
  alerts: { critical: number; warning: number; info: number; total: number };
}

export interface ChartPoint {
  t: string;
  v: number;
}

export interface ChartData {
  field_id: string;
  sensor: string;
  period_hours: number;
  points: ChartPoint[];
}

export interface WebSocketMessage {
  event: string;
  field_id: string;
  irrigation_status?: IrrigationDecision;
  irrigation_severity?: Severity;
  soil_moisture_pct?: number;
  air_temperature_c?: number;
  air_humidity_pct?: number;
  water_level_available?: boolean;
  source?: string;
  server_timestamp: string;
}
