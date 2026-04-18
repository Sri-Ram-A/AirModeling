"""
backend/services/data_loader.py
Cached helpers for loading CSV data from disk.
Uses functools.lru_cache so each file is read only once per process —
no database needed, but still fast on repeated requests.
Run this file directly in VS Code (Ctrl+Shift+F5) to verify paths.
"""

from __future__ import annotations
import functools
import pandas as pd
from loguru import logger
from src.config import IMPUTED_CSV, MASTER_CSV, STATIONS_CSV,_require_file


# Stations metadata
@functools.lru_cache(maxsize=1)
def load_stations() -> pd.DataFrame:
    """
    Purpose
    - Load station metadata from CSV
    - Normalise column names.
    ---
    Returns
    pd.DataFrame with columns: name, latitude, longitude, site_id, organization
    """
    df = pd.read_csv(_require_file(STATIONS_CSV))
    # Normalise to a consistent schema regardless of source-file casing
    rename_map = {
        "StationName": "name",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "SiteID": "site_id",
        "Organization": "organization",
    }
    df = df.rename(columns=rename_map)
    required = {"name", "latitude", "longitude", "site_id", "organization"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"stations.csv is missing columns: {missing}")
    logger.success(f"Loaded {len(df)} stations.")
    return df.reset_index(drop=True)


# Master / imputed sensor dataset
@functools.lru_cache(maxsize=1)
def load_master() -> pd.DataFrame:
    """
    Load the imputed master dataset.
    -------
    Falls back to the raw master if the imputed file doesn't exist yet.
    Returns
    pd.DataFrame with a parsed 'time' column.
    ### Index(
    ['time', 'pm25', 'pm10', 'no', 'no2', 'nox', 'nh3', 'so2', 'co', 'o3',
        'benzene', 'toluene', 'ethyl_benzene', 'mp_xylene',
        'average_temperature', 'relative_humidity', 'wind_speed',
        'wind_direction', 'rainfall', 'total_rainfall', 'solar_radiation',
        'pressure', 'station_name', 'site', 'org', 'latitude', 'longitude'],
    dtype='str'
    ### )
    """
    path = IMPUTED_CSV if IMPUTED_CSV.exists() else MASTER_CSV
    df = pd.read_csv(_require_file(path), parse_dates=["time"])
    logger.success(f"Loaded {len(df):,} rows from {path.name}.")
    return df


# Dev entrypoint
if __name__ == "__main__":
    stations = load_stations()
    print("=== Stations ===")
    print(stations.head())
    print(f"\nColumns: {list(stations.columns)}")
    print(f"Total  : {len(stations)}")

    master = load_master()
    print("\n=== Master dataset ===")
    print(master.head())
    print(f"\nColumns: {list(master.columns)}")
    print(f"Total  : {len(master):,} rows")
    print(f"Stations: {master['station_name'].nunique()}")
