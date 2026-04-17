# interactive_analysis.py
# Run this in IPython or Jupyter for step-by-step debugging

from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import sys

# Paths
ROOT_DIR = Path.cwd()  # Adjust if needed
MASTER_PATH = ROOT_DIR / "backend" / "data" / "artifacts" / "master_dataset.csv"
STATIONS_PATH = ROOT_DIR / "backend" / "data" / "raw" / "stations.csv"

# Load data
logger.info("Loading master dataset...")
master_df = pd.read_csv(MASTER_PATH)
master_df['time'] = pd.to_datetime(master_df['time'])
logger.success(f"Loaded {len(master_df)} rows")

logger.info("Loading stations metadata...")
stations_df = pd.read_csv(STATIONS_PATH)
logger.success(f"Loaded {len(stations_df)} stations")

# RVCE coordinates
RVCE_LAT = 12.921418
RVCE_LON = 77.502466

# Calculate distances function
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# Find nearest stations
logger.info("Calculating distances from RVCE to all stations...")
distances = []
for _, row in stations_df.iterrows():
    dist = haversine_distance(RVCE_LAT, RVCE_LON, row['Latitude'], row['Longitude'])
    distances.append({
        'station': row['StationName'],
        'distance_km': dist,
        'latitude': row['Latitude'],
        'longitude': row['Longitude']
    })

distances_df = pd.DataFrame(distances)
distances_df = distances_df.sort_values('distance_km')

# Display results
print("\n" + "="*60)
print("TOP 10 NEAREST STATIONS TO RVCE")
print("="*60)
for i, row in distances_df.head(10).iterrows():
    print(f"{row['station']:30s} | {row['distance_km']:.2f} km")

# Check what data is available for these stations at a specific time
test_time = "2025-01-01 00:00:00"
nearest_stations = distances_df.head(5)['station'].tolist()

logger.info(f"Checking data availability at {test_time} for nearest stations...")
available_data = master_df[
    (master_df['time'] == test_time) & 
    (master_df['station_name'].isin(nearest_stations))
]

print(f"\nData available for {test_time}:")
print(available_data[['station_name', 'pm25', 'pm10', 'wind_speed', 'wind_direction']].to_string())

# Check for missing values
logger.info("Checking for missing values in key columns...")
key_columns = ['pm25', 'pm10', 'wind_speed', 'wind_direction']
for col in key_columns:
    missing = available_data[col].isna().sum()
    logger.info(f"{col}: {missing} missing values out of {len(available_data)}")