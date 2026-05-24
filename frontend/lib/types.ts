export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type SolverMethod = "lstsq" | "nnls" | "tikhonov" | "truncated_svd";

export interface BackendError {
  message?: string;
  error?: string;
  detail?: string;
}

export interface StationMeta {
  station_name: string;
  latitude: number;
  longitude: number;
}

export interface StationReading {
  station_name: string;
  pollutant: number;
  wind_speed: number;
  wind_direction: number;
  solar_radiation: number;
  timestamp: string;
}

export interface CurrentReadingResponse {
  timestamp: string;
  pollutant: string;
  station_count: number;
  complete_station_count: number;
  readings: StationReading[];
}

export interface TransportMatrixResponse {
  timestamp: string;
  pollutant: string;
  station_names: string[];
  stability_classes: string[];
  transport_matrix: number[][];
  current_reading: number[];
}

export interface ContributionResponse {
  method: SolverMethod;
  timestamp: string;
  pollutant: string;
  residual_norm: number;
  rank: number | null;
  condition_number: number | null;
  observed_concentrations: number[];
  estimated_emissions: number[];
  reconstructed_concentrations: number[];
  residuals: number[];
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
}
