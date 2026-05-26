# app/data.py
"""
Global data layer.

Loads stations.csv and master_dataset.csv exactly once at import time.
All functions operate on the module-level DataFrames - no classes, no DI.
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger

_BASE = Path(__file__).resolve().parents[1]
STATIONS_FILE = _BASE / "data" / "raw" / "stations.csv"
MASTER_FILE = _BASE / "data" / "artifacts" / "final_master_dataset.csv"
MIN_COMPLETE_STATIONS = 10  # minimum stations required for a snapshot to be "usable"

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

# Load once at import time
stations_df: pd.DataFrame = pd.read_csv(STATIONS_FILE)
stations_df["latitude"] = pd.to_numeric(stations_df["latitude"], errors="coerce")
stations_df["longitude"] = pd.to_numeric(stations_df["longitude"], errors="coerce")

STATION_NAMES: list[str] = stations_df["station_name"].dropna().astype(str).tolist()
_station_order: dict[str, int] = {n: i for i, n in enumerate(STATION_NAMES)}
_station_meta: pd.DataFrame = stations_df.set_index("station_name")

master_df: pd.DataFrame = pd.read_csv(MASTER_FILE, parse_dates=["time"])
master_df["time"] = pd.to_datetime(master_df["time"], errors="coerce")
master_df = master_df[master_df["station_name"].isin(STATION_NAMES)].copy()

logger.info(
    f"Data loaded | stations={len(STATION_NAMES)} | master_rows={len(master_df)}"
)


def station_coordinates() -> tuple[np.ndarray, np.ndarray]:
    """Return (lats, lons) in canonical station order."""
    meta = _station_meta.reindex(STATION_NAMES)
    lats = pd.to_numeric(meta["latitude"], errors="coerce").to_numpy(dtype=float)
    lons = pd.to_numeric(meta["longitude"], errors="coerce").to_numpy(dtype=float)
    return lats, lons


def validate_pollutant(pollutant: str) -> None:
    """Raise ValueError if pollutant is not in the allowed list."""
    if pollutant not in POLLUTANT_COLS:
        raise ValueError(f"Unknown pollutant '{pollutant}'. Allowed: {POLLUTANT_COLS}")


def _pick_latest_usable_time(
    df: pd.DataFrame,
    required_cols: list[str],
) -> pd.Timestamp:
    """
    From df, pick the most recent timestamp where at least
    MIN_COMPLETE_STATIONS stations have non-null values for required_cols.
    Falls back to the global max timestamp if nothing qualifies.
    """
    usable = df.dropna(subset=required_cols)
    coverage = usable.groupby("time")["station_name"].nunique()
    valid = coverage[coverage >= MIN_COMPLETE_STATIONS]
    if valid.empty:
        logger.warning("No snapshot meets the completeness threshold - using latest.")
        return pd.Timestamp(df["time"].max())
    return pd.Timestamp(valid.index.max())


def get_snapshot(
    timestamp: pd.Timestamp | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Return one snapshot (all rows for a single timestamp).

    Parameters
    ----------
    timestamp:
        - None          → latest usable snapshot across the whole dataset.
        - date-only     → latest usable snapshot on that calendar day.
        - full datetime → exact match.
    columns:
        Extra columns (beyond meteo) required to be non-null when choosing
        a usable snapshot.  Pass [pollutant] for inversion endpoints.
        If None, only meteorology completeness is checked.
    """
    # 1. Get required columns for usability check
    required = ["wind_speed", "wind_direction", "solar_radiation"]
    if columns:
        for col in columns:
            if col not in required:
                required.append(col)

    scoped = master_df.copy()

    # 2. Parse timestamp if provided, and filter scoped df accordingly
    if timestamp is not None:
        ts = pd.Timestamp(timestamp)
        is_date_only = (
            ts.time() == pd.Timestamp("00:00:00").time()
            and len(str(timestamp).strip()) <= 10
        )

        if is_date_only:
            day_df = scoped[
                (scoped["time"] >= ts.normalize())
                & (scoped["time"] < ts.normalize() + pd.Timedelta(days=1))
            ]
            if day_df.empty:
                raise ValueError(f"No data for date: {ts.date()}")
            selected = _pick_latest_usable_time(day_df, required)
            snap = day_df[day_df["time"] == selected]
        else:
            snap = scoped[scoped["time"] == ts]
            if snap.empty:
                raise ValueError(f"No data for timestamp: {ts}")

        logger.info(f"Snapshot | ts={snap['time'].iloc[0]} | rows={len(snap)}")
        return snap.copy()

    # 3. No timestamp provided - pick the latest usable snapshot across the whole dataset
    selected = _pick_latest_usable_time(scoped, required)
    snap = scoped[scoped["time"] == selected]
    if snap.empty:
        raise ValueError("No usable snapshot found.")
    logger.info(f"Snapshot (latest) | ts={selected} | rows={len(snap)}")
    return snap.copy()


def get_window(
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """
    Return all rows between start (inclusive) and end.
    If end has no time component (date-only), +1 day is applied so the
    whole day is included.
    """
    # 1. Make end inclusive for date-only inputs
    if end.time() == pd.Timestamp("00:00:00").time():
        end = end + pd.Timedelta(days=1)
    windowed = master_df[
        (master_df["time"] >= start) & (master_df["time"] < end)
    ].copy()
    logger.info(
        f"Window | {start} → {end} | rows={len(windowed)} | timestamps={windowed['time'].nunique()}"
    )
    return windowed


def align_to_stations(
    df: pd.DataFrame,
    cols: list[str],
) -> dict[str, np.ndarray]:
    """
    Reindex df by canonical station order and return numeric arrays per column.
    Missing stations get NaN.
    """
    indexed = df.set_index("station_name").reindex(STATION_NAMES)
    result: dict[str, np.ndarray] = {}
    for col in cols:
        if col in indexed.columns:
            result[col] = pd.to_numeric(indexed[col], errors="coerce").to_numpy(float)
        else:
            result[col] = np.full(len(STATION_NAMES), np.nan)
    return result


def impute_median(arr: np.ndarray) -> np.ndarray:
    """Replace NaN with column median; return zeros if everything is NaN."""
    if np.all(np.isnan(arr)):
        return np.zeros_like(arr)
    out = arr.copy()
    out[np.isnan(out)] = float(np.nanmedian(out))
    return out


def sort_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by time, then by canonical station order."""
    df = df.copy()
    df["_order"] = df["station_name"].map(_station_order)
    return df.sort_values(["time", "_order"]).drop(columns="_order")
