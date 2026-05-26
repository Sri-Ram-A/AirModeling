# app/data.py
"""
Global data layer.

Loads stations.csv and master_dataset.csv exactly once at import time.
All functions operate on the module-level DataFrames - no classes, no DI.
"""

from __future__ import annotations
from datetime import time as dt_time
from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger

# CONFIGURATION & CONSTANTS
BASE = Path(__file__).resolve().parents[1]
STATIONS_FILE = BASE / "data" / "raw" / "stations.csv"
MASTER_FILE = BASE / "data" / "artifacts" / "final_master_dataset.csv"

MIN_COMPLETE_STATIONS = 10
DEFAULT_REQUIRED_COLS = ["wind_speed", "wind_direction", "solar_radiation"]

POLLUTANT_COLS = [
    "pm25",
    "pm10",
    "no",
    "no2",
    "nox",
    "nh3",
    "so2",
    "co",
    "o3",
    "benzene",
    "toluene",
]

METEO_COLS = [
    "average_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "rainfall",
    "total_rainfall",
    "solar_radiation",
    "pressure",
]


# PRIVATE DATA ETL HELPERS
def _load_stations_pipeline(path: Path) -> pd.DataFrame:
    """Load, parse, and clean the stations database."""
    df = pd.read_csv(path)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df


def _load_master_pipeline(path: Path, valid_stations: list[str]) -> pd.DataFrame:
    """Load, parse, and filter the master dataset against valid stations."""
    df = pd.read_csv(path, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    return df[df["station_name"].isin(valid_stations)].copy()


def _is_date_only(timestamp: pd.Timestamp | str) -> bool:
    """Determine if the provided timestamp input is intended as a date-only filter."""
    if isinstance(timestamp, str):
        return len(timestamp.strip()) <= 10
    return timestamp.time() == dt_time(0, 0, 0)


def _pick_latest_usable_time(
    df: pd.DataFrame, required_cols: list[str]
) -> pd.Timestamp:
    """Find the most recent timestamp meeting the station coverage threshold."""
    usable = df.dropna(subset=required_cols)
    coverage = usable.groupby("time")["station_name"].nunique()
    valid_times = coverage[coverage >= MIN_COMPLETE_STATIONS]
    if valid_times.empty:
        logger.warning(
            "No snapshot meets completeness threshold; falling back to absolute max."
        )
        return pd.Timestamp(df["time"].max())
    return pd.Timestamp(valid_times.index.max())


# INITIALIZATION (Runs once at import time)
stations_df = _load_stations_pipeline(STATIONS_FILE)
STATION_NAMES: list[str] = stations_df["station_name"].dropna().astype(str).tolist()
station_order: dict[str, int] = {name: idx for idx, name in enumerate(STATION_NAMES)}
master_df = _load_master_pipeline(MASTER_FILE, STATION_NAMES)
logger.info(
    f"Data layer initialized | stations={len(STATION_NAMES)} | master_rows={len(master_df)}"
)


# PUBLIC API FUNCTIONS
def station_coordinates() -> tuple[np.ndarray, np.ndarray]:
    """Return (lats, lons) numpy arrays perfectly aligned to canonical station order."""
    lats = pd.to_numeric(stations_df["latitude"], errors="coerce").to_numpy(dtype=float)
    lons = pd.to_numeric(stations_df["longitude"], errors="coerce").to_numpy(
        dtype=float
    )
    return lats, lons


def validate_pollutant(pollutant: str) -> None:
    """Raise ValueError if the pollutant is unmapped."""
    if pollutant not in POLLUTANT_COLS:
        raise ValueError(f"Unknown pollutant '{pollutant}'. Allowed: {POLLUTANT_COLS}")


def get_snapshot(
    timestamp: pd.Timestamp | str | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Return one snapshot (all rows for a single timestamp).
    Routes logic based on timestamp specificity (None -> global latest, Date -> daily latest, Datetime -> exact).
    """
    # 1. Resolve column rules cleanly using a unique list merge
    required = list(set(DEFAULT_REQUIRED_COLS + (columns or [])))
    # Case A: No timestamp provided -> get latest valid snapshot across whole dataset
    if timestamp is None:
        selected_time = _pick_latest_usable_time(master_df, required)
        snapshot = master_df[master_df["time"] == selected_time]
        if snapshot.empty:
            raise ValueError("No usable snapshot found in entire dataset.")
        logger.info(
            f"Snapshot (latest global) | ts={selected_time} | rows={len(snapshot)}"
        )
        return snapshot.copy()
    ts = pd.Timestamp(timestamp)

    # Case B: Date-only provided -> get latest valid snapshot within that calendar day
    if _is_date_only(timestamp):
        day_start = ts.normalize()
        day_end = day_start + pd.Timedelta(days=1)
        day_df = master_df[
            (master_df["time"] >= day_start) & (master_df["time"] < day_end)
        ]
        if day_df.empty:
            raise ValueError(f"No data found for date: {ts.date()}")
        selected_time = _pick_latest_usable_time(day_df, required)
        snapshot = day_df[day_df["time"] == selected_time]
        logger.info(
            f"Snapshot (latest for day) | ts={selected_time} | rows={len(snapshot)}"
        )
        return snapshot.copy()

    # Case C: Exact datetime provided -> fetch exact match
    snapshot = master_df[master_df["time"] == ts]
    if snapshot.empty:
        raise ValueError(f"No data matches exact timestamp: {ts}")

    logger.info(f"Snapshot (exact match) | ts={ts} | rows={len(snapshot)}")
    return snapshot.copy()


def get_window(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return all data rows falling inside the inclusive/exclusive window bounds."""
    # Convert date-only end bounds to be inclusive of that entire day
    adjusted_end = end + pd.Timedelta(days=1) if end.time() == dt_time(0, 0, 0) else end
    windowed = master_df[
        (master_df["time"] >= start) & (master_df["time"] < adjusted_end)
    ].copy()
    logger.info(f"Window extracted | {start} -> {adjusted_end} | rows={len(windowed)}")
    return windowed


def align_to_stations(df: pd.DataFrame, cols: list[str]) -> dict[str, np.ndarray]:
    """Reindex df by canonical station order, outputting dictionary of clean numpy float arrays."""
    # 1.1 Sets the Index: It temporarily turns the "station_name" column into the row labels (index).
    # 1.2 Reindexes: It forces the rows to match a predefined, global list called STATION_NAMES.
    indexed = df.set_index("station_name").reindex(STATION_NAMES)
    return {
        col: pd.to_numeric(indexed[col], errors="coerce").to_numpy(dtype=float)
        if col in indexed.columns
        else np.full(len(STATION_NAMES), np.nan)
        for col in cols
    }


def impute_median(arr: np.ndarray) -> np.ndarray:
    """Replace NaN values with array median; falls back to zeros if fully empty."""
    if np.all(np.isnan(arr)):
        return np.zeros_like(arr)
    output = arr.copy()
    output[np.isnan(output)] = float(np.nanmedian(output))
    return output


def sort_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Sort Dataframe strictly by time sequence, then by canonical station sequence."""
    df = df.copy()
    df["_order"] = df["station_name"].map(station_order)
    return df.sort_values(["time", "_order"]).drop(columns="_order")
