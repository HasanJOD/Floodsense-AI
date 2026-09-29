export type RiskBand = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';

export interface FloodProbabilityResponse {
  location_name: string | null;
  latitude: number;
  longitude: number;
  flood_probability: number;
  risk_band: RiskBand;
  class_probabilities: Record<RiskBand, number>;
  method: string;
  model_limitations: string;
  rain_1h: number;
  rain_6h: number;
  rain_24h: number;
  elevation_m: number;
  soil_moisture: number;
  source: string;
  weather_timestamp: string | null;
  fetch_timestamp: string | null;
  stale: boolean;
}

export interface MonitoredLocation {
  id: number;
  name: string;
  lat: number;
  lon: number;
  threshold: number;
  last_check: number | null;
  last_probability: number | null;
  last_band: RiskBand | null;
  alert: boolean;
  stale: boolean;
}

export interface MonitoredLocationInput {
  name: string;
  lat: number;
  lon: number;
  threshold: number;
}

export interface MonitoredListResponse {
  locations: MonitoredLocation[];
}