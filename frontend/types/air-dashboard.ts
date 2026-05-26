// types/air-dashboard.ts
// Shared types derived from OpenAPI schema — keep co-located with dashboard pages

export type StationRow = {
  time: string;
  station_name: string;
  latitude: number | null;
  longitude: number | null;
  site: string | number | null;
  org: string | null;
  pm25: number | null;
  pm10: number | null;
  no: number | null;
  no2: number | null;
  nox: number | null;
  nh3: number | null;
  so2: number | null;
  co: number | null;
  o3: number | null;
  benzene: number | null;
  toluene: number | null;
  average_temperature: number | null;
  relative_humidity: number | null;
  wind_speed: number | null;
  wind_direction: number | null;
  rainfall: number | null;
  total_rainfall: number | null;
  solar_radiation: number | null;
  pressure: number | null;
};

export type SolverResult = {
  method: string;
  residual_norm: number;
  Q: number[];
  reconstructed_C: number[];
  residuals: number[];
  negative_q_count: number;
  metadata: Record<string, unknown> | null;
};

export type MatrixDiagnostics = {
  shape: number[];
  rank: number;
  condition_number: number | null;
  singular_values: number[];
};

export type InversionResponse = {
  timestamp: string;
  pollutant: string;
  station_names: string[];
  stability_classes: string[];
  observed_concentrations: number[];
  solutions: SolverResult[];
  diagnostics: MatrixDiagnostics;
};

export const POLLUTANTS = [
  "pm25", "pm10", "no", "no2", "nox",
  "nh3", "so2", "co", "o3", "benzene", "toluene",
] as const;

export type PollutantKey = typeof POLLUTANTS[number];

export const POLLUTANT_LABELS: Record<PollutantKey, string> = {
  pm25: "PM2.5", pm10: "PM10", no: "NO", no2: "NO₂",
  nox: "NOₓ", nh3: "NH₃", so2: "SO₂", co: "CO",
  o3: "O₃", benzene: "Benzene", toluene: "Toluene",
};

export const POLLUTANT_UNITS: Record<PollutantKey, string> = {
  pm25: "µg/m³", pm10: "µg/m³", no: "µg/m³", no2: "µg/m³",
  nox: "µg/m³", nh3: "µg/m³", so2: "µg/m³", co: "mg/m³",
  o3: "µg/m³", benzene: "µg/m³", toluene: "µg/m³",
};