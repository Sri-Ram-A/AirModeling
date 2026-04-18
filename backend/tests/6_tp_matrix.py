# Step 1: Calculate downwind distance (x) and crosswind distance (y)
#         First, compute:
#         - Distance between source and target (d_km) using haversine formula
#         - Bearing (angle from source to target) using atan2 formula
#         - Wind direction (θ_wind) from your data (in degrees, where 0° = North)
#         Then:
#         x = d_km × 1000 × cos(θ_wind - bearing)  [downwind distance in meters]
#         y = d_km × 1000 × sin(θ_wind - bearing)  [crosswind distance in meters]
#         IMPORTANT:
#         - If x < 0, the target is UPWIND of source (source cannot affect target)
#         - In this case, T = 0 (no contribution)

# Step 2: Determine atmospheric stability class (A through F)
#         Based on:
#         - Wind speed (u) from your data
#         - Time of day (day vs night)
#         - Solar radiation (from your data)
#         Simplified rule (Pasquill):
#         - u < 2 m/s + strong sun → A (very unstable)
#         - u < 3 m/s + moderate sun → B (unstable)
#         - u < 5 m/s + weak sun → C (slightly unstable)
#         - u > 5 m/s or overcast → D (neutral)
#         - u < 3 m/s + night + clear → E (slightly stable)
#         - u < 2 m/s + night + clear → F (stable)

# Step 3: Calculate dispersion coefficients σ_y and σ_z
#         Using Pasquill-Gifford formulas:
#         σ_y = a_y × x^b_y
#         σ_z = a_z × x^b_z
#         Where coefficients depend on stability class:
#         ┌─────────┬──────────┬──────────┬──────────┬──────────┐
#         │ Class   │   a_y    │   b_y    │   a_z    │   b_z    │
#         ├─────────┼──────────┼──────────┼──────────┼──────────┤
#         │ A       │ 0.36     │ 0.90     │ 0.00023  │ 2.10     │
#         │ B       │ 0.25     │ 0.90     │ 0.058    │ 1.09     │
#         │ C       │ 0.19     │ 0.90     │ 0.11     │ 0.91     │
#         │ D       │ 0.13     │ 0.90     │ 0.57     │ 0.58     │
#         │ E       │ 0.096    │ 0.90     │ 0.85     │ 0.47     │
#         │ F       │ 0.063    │ 0.90     │ 0.77     │ 0.42     │
#         └─────────┴──────────┴──────────┴──────────┴──────────┘

# Step 4: Apply Gaussian plume formula (ground-level sensor)
#         T = 1 / (π × u × σ_y × σ_z) × exp(-y²/(2σ_y²)) × exp(-H²/(2σ_z²))
#         Where:
#         - H = effective stack height (assume 20m for now)
#         - u = wind speed (m/s) from your data

# Step 5: Apply unit conversion
#         The formula above gives T in (g/m³) / (g/s) = s/m³
#         But we want C in µg/m³ and Q in g/s, so:
#         T_actual = T × 1,000,000  [to convert g/m³ to µg/m³]
#         Final: C (µg/m³) = T_actual × Q (g/s)

"""
Extracts weather data from master dataset and builds transport matrix.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
from datetime import datetime
from typing import List
from backend.services.gaussian_plume import GaussianPlumeModel, TransportMatrixBuilder

# Configure logger
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO")

def load_station_metadata(stations_csv_path: Path) -> pd.DataFrame:
    """Load station metadata from CSV"""
    stations_df = pd.read_csv(stations_csv_path)
    stations_df = stations_df.rename(columns={
        'StationName': 'name',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    })
    logger.info(f"Loaded {len(stations_df)} stations from metadata")
    return stations_df[['name', 'latitude', 'longitude']]

def get_weather_at_time(master_df: pd.DataFrame, 
                        station_name: str, 
                        target_time: datetime) -> pd.Series:
    """
    Extract weather data for a specific station at a specific time.
    
    Args:
        master_df: Imputed master dataset
        station_name: Name of the station to use for weather data
        target_time: Timestamp to query
        
    Returns:
        Series with weather columns
    """
    mask = (master_df['station_name'] == station_name) & (master_df['time'] == target_time)
    weather_row = master_df[mask]
    
    if weather_row.empty:
        logger.warning(f"No weather data found for {station_name} at {target_time}")
        # Return default values
        return pd.Series({
            'wind_speed': 2.0,
            'wind_direction': 180.0,
            'solar_radiation': 300.0,
            'time': target_time
        })
    
    weather_row = weather_row.iloc[0]
    
    return pd.Series({
        'wind_speed': weather_row.get('wind_speed', 2.0),
        'wind_direction': weather_row.get('wind_direction', 180.0),
        'solar_radiation': weather_row.get('solar_radiation', 300.0),
        'time': target_time
    })

def build_transport_matrix_for_target(master_df: pd.DataFrame,
                                       stations_metadata: pd.DataFrame,
                                       target_station_name: str,
                                       source_station_names: List[str],
                                       target_time: datetime,
                                       weather_station_name: str|None = None) -> np.ndarray:
    """
    Build transport matrix for a specific target and time.
    
    Args:
        master_df: Imputed master dataset
        stations_metadata: DataFrame with station coordinates
        target_station_name: Name of target station (e.g., 'RVCE-Mailasandra')
        source_station_names: List of source station names
        target_time: Timestamp for calculation
        weather_station_name: Station to use for weather data (defaults to target)
        
    Returns:
        T_matrix: numpy array of shape (1, n_sources) if using single target
    """
    # Get coordinates
    target_coords = stations_metadata[stations_metadata['name'] == target_station_name]
    if target_coords.empty:
        raise ValueError(f"Target station '{target_station_name}' not found in metadata")
    
    sources_coords = stations_metadata[stations_metadata['name'].isin(source_station_names)]
    if len(sources_coords) != len(source_station_names):
        missing = set(source_station_names) - set(sources_coords['name'])
        raise ValueError(f"Source stations not found: {missing}")
    
    # Get weather data
    weather_station = weather_station_name or target_station_name
    weather = get_weather_at_time(master_df, weather_station, target_time)
    
    logger.info(f"Target: {target_station_name}")
    logger.info(f"Sources: {source_station_names}")
    logger.info(f"Weather from: {weather_station}")
    logger.info(f"Time: {target_time}")
    logger.info(f"Wind: {weather['wind_speed']} m/s, {weather['wind_direction']}°")
    
    # Initialize model and builder
    model = GaussianPlumeModel(stack_height=20.0)
    builder = TransportMatrixBuilder(model)
    
    # Build T matrix
    T_matrix = builder.build_matrix(
        sources_df=sources_coords,
        targets_df=target_coords,
        wind_speed=weather['wind_speed'],
        wind_direction=weather['wind_direction'],
        solar_radiation=weather.get('solar_radiation'),
        time_of_day='day' if 6 <= target_time.hour <= 18 else 'night'
    )
    
    return T_matrix

# Example usage
if __name__ == "__main__":
    # Setup paths
    ROOT_DIR = Path(__file__).resolve().parent.parent
    IMPUTED_PATH = ROOT_DIR / "backend" / "data" / "artifacts" / "imputed_master_dataset.csv"
    STATIONS_PATH = ROOT_DIR / "backend" / "data" / "raw" / "stations.csv"
    
    # Load data
    logger.info("Loading imputed master dataset...")
    master_df = pd.read_csv(IMPUTED_PATH)
    master_df['time'] = pd.to_datetime(master_df['time'])
    stations_metadata = load_station_metadata(STATIONS_PATH)
    
    # Define target and sources
    target = 'RVCE-Mailasandra'
    sources = ['BtmLayout', 'BapujiNagar', 'CityRailwayStation', 'Hebbal', 'Peenya']
    # Define time
    target_time = pd.to_datetime('2025-01-01 00:00:00')
    # Build T matrix
    T = build_transport_matrix_for_target(
        master_df=master_df,
        stations_metadata=stations_metadata,
        target_station_name=target,
        source_station_names=sources,
        target_time=target_time
    )
    print(f"\nTransport Matrix T (shape {T.shape}):")
    print(T)