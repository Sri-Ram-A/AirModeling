export interface PollutantReadings {
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
}

export interface MeteorologyReadings {
    average_temperature: number | null;
    relative_humidity: number | null;
    wind_speed: number | null;
    wind_direction: number | null;
    rainfall: number | null;
    total_rainfall: number | null;
    solar_radiation: number | null;
    pressure: number | null;
}

export interface StationSnapshot {
    station_name: string;
    latitude: number;
    longitude: number;
    pollutants: PollutantReadings;
    meteorology: MeteorologyReadings;
}

export interface CurrentReadingResponse {
    timestamp: string;
    total_stations: number;
    stations_in_snapshot: number;
    selected_pollutant: string;
    readings: StationSnapshot[];
}

