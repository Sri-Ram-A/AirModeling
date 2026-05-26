# app/endpoints/dashboard.py

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
import app.data as data
from app.schemas import StationRow

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Response columns - centralised so both endpoints stay consistent
_RESPONSE_COLS = [
    "time",
    "station_name",
    "latitude",
    "longitude",
    "site",
    "org",
    *data.POLLUTANT_COLS,
    *data.METEO_COLS,
]


def _df_to_station_rows(df: pd.DataFrame) -> list[StationRow]:
    """Convert a DataFrame to a list of StationRow, sorted canonically."""
    df = data.sort_rows(df).copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce").astype(str)
    df = df.replace({np.nan: None})
    # Keep only columns that exist in the DataFrame
    cols = [c for c in _RESPONSE_COLS if c in df.columns]
    records = df[cols].to_dict(orient="records")
    return [StationRow.model_validate(r) for r in records]


# GET /dashboard/current_reading
@router.get(
    "/current_reading",
    response_model=list[StationRow],
    summary="Latest snapshot for all stations",
    description=(
        "Returns the most recent usable snapshot across all stations. "
        "Pass `timestamp` to pin to a specific time or date. "
        "Pass `pollutant` to enforce non-null values for that column when "
        "choosing which snapshot is 'usable'."
    ),
)
def get_current_reading(
    timestamp: str | None = Query(
        default=None,
        description=(
            "ISO-8601 timestamp. Examples: `2025-05-25`, `2025-05-25T14:00:00`. "
            "Omit for the latest valid snapshot. Date-only returns the latest "
            "valid snapshot on that day."
        ),
    ),
    pollutant: str | None = Query(
        default=None,
        description=(
            "Pollutant used to filter usable snapshots. "
            "If omitted, only meteorology completeness is checked."
        ),
    ),
) -> list[StationRow]:
    # 1. Validate pollutant if provided.
    if pollutant:
        try:
            data.validate_pollutant(pollutant)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 2. Parse timestamp string into pandas Timestamp (or None).
    ts: pd.Timestamp | None = pd.to_datetime(timestamp) if timestamp else None
    # 3. Fetch the snapshot from the global DataFrame.
    try:
        snap = data.get_snapshot(
            timestamp=ts,
            columns=[pollutant] if pollutant else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # 4. Convert to response schema.
    rows: list[StationRow] = _df_to_station_rows(snap)
    logger.info(
        f"GET /current_reading | ts={timestamp or 'latest'} | pollutant={pollutant or 'all'} | rows={len(rows)}"
    )
    return rows


# GET /dashboard/current_reading/window
@router.get(
    "/current_reading/window",
    response_model=list[StationRow],
    summary="Station readings over a time window",
    description=(
        "Returns all station rows between `start_timestamp` and `end_timestamp` "
        "(inclusive). The response is flat; group by `time` on the frontend."
    ),
)
def get_current_reading_window(
    start_timestamp: str = Query(..., description="Start of the window (ISO-8601)."),
    end_timestamp: str = Query(..., description="End of the window (ISO-8601)."),
    pollutant: str | None = Query(
        default=None,
        description="Optional. When provided, only rows with non-null values for "
        "this pollutant are returned.",
    ),
) -> list[StationRow]:
    # 1. Validate pollutant if provided.
    if pollutant:
        try:
            data.validate_pollutant(pollutant)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    # 2. Parse timestamps.
    try:
        start: pd.Timestamp = pd.to_datetime(start_timestamp)
        end: pd.Timestamp = pd.to_datetime(end_timestamp)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid timestamp format: {exc}"
        ) from exc
    # 3. Fetch the time window from the global DataFrame.
    window = data.get_window(start=start, end=end)
    # 4. Optionally drop rows missing the requested pollutant.
    if pollutant and not window.empty:
        window = window.dropna(subset=[pollutant])
    # 5. Convert to response schema.
    rows: list[StationRow] = _df_to_station_rows(window)
    logger.info(
        f"GET /current_reading/window | {start_timestamp} → {end_timestamp} | pollutant={pollutant or 'all'} | rows={len(rows)}"
    )
    return rows
