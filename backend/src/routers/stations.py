"""
backend/routers/stations.py
Endpoints related to station metadata and sensor time-series data.
Endpoints
---------
GET  /stations/                         — list all stations
GET  /stations/map                      — returns folium HTML map
GET  /stations/{station_name}/monthly   — monthly sensor readings
GET  /stations/{station_name}/data      — paginated raw sensor data
Run interactively in VS Code:
    python -m backend.routers.stations
"""

from __future__ import annotations
import io
from datetime import datetime
from typing import List, Optional
import folium
import pandas as pd
from fastapi.responses import HTMLResponse
from loguru import logger
from fastapi import APIRouter, HTTPException, Query

from src.schemas.stations import MonthlyStationData, SensorReading, Station, SENSOR_COLS
from src.services.data_loader import load_master, load_stations

router = APIRouter()


# GET /stations/
@router.get(
    "/",
    response_model=List[Station],
    summary="List all monitoring stations",
)
def get_stations() -> List[Station]:
    """
    Return name, organisation, latitude and longitude for every station
    in stations.csv.
    """
    df = load_stations()
    stations = []
    for _, row in df.iterrows():
        stations.append(
            Station(
                name=row["name"],
                organization=row.get("organization"),
                latitude=row["latitude"],
                longitude=row["longitude"],
                site_id=row["site_id"],
            )
        )
    logger.info(f"Returning {len(stations)} stations.")
    return stations


# GET /stations/map
@router.get(
    "/map",
    response_class=HTMLResponse,
    summary="Interactive Folium map of all stations",
)
def get_stations_map() -> HTMLResponse:
    """
    Returns an HTML page containing an interactive Folium map.
    Each station has a clickable marker showing its name and organisation.
    """
    df = load_stations()
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()
    folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=11)
    for index, row in df.iterrows():
        tooltip_text = row["name"]
        if "organization" in df.columns and pd.notna(row.get("organization")):
            tooltip_text = f"{row['name']} ({row['organization']})"
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            tooltip=folium.Tooltip(tooltip_text, sticky=True),
            popup=folium.Popup(row["name"], max_width=200),
        ).add_to(folium_map)

    # Render to HTML string (no file I/O needed for the API response)
    html_buffer = io.BytesIO()
    folium_map.save(html_buffer, close_file=False)
    html_content = html_buffer.getvalue().decode("utf-8")

    logger.info("Returning stations map HTML.")
    return HTMLResponse(content=html_content)


# GET /stations/{station_name}/monthly
@router.get(
    "/{station_name}/monthly",
    response_model=MonthlyStationData,
    summary="Monthly sensor readings for a station",
)
def get_monthly_data(
    station_name: str,
    year: int = Query(..., ge=2000, le=2100, description="4-digit year"),
    month: int = Query(..., ge=1, le=12, description="Month number (1-12)"),
) -> MonthlyStationData:
    """
    Return every 15-minute reading for **station_name** in the given year/month.
    - **station_name**: must match a value in the `station_name` column of the dataset.
    - **year** / **month**: filter the time index to that calendar month.
    """
    df = load_master()
    # Case-insensitive station match
    mask_station = df["station_name"].str.lower() == station_name.lower()
    station_df = df[mask_station]
    if station_df.empty:
        available = sorted(df["station_name"].unique().tolist())
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Station '{station_name}' not found.",
                "available_stations": available,
            },
        )
    mask_time = (station_df["time"].dt.year == year) & (
        station_df["time"].dt.month == month
    )
    month_df = station_df[mask_time].sort_values("time")
    if month_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data for station '{station_name}' in {year}-{month:02d}.",
        )
    # Build response
    readings = _dataframe_to_readings(month_df)
    logger.info(
        f"Returning {len(readings)} readings for {station_name} ({year}-{month:02d})."
    )
    return MonthlyStationData(
        station_name=station_name,
        year=year,
        month=month,
        total_readings=len(readings),
        readings=readings,
    )


# GET /stations/{station_name}/data   (paginated)
@router.get(
    "/{station_name}/data",
    summary="Paginated raw sensor readings for a station",
)
def get_station_data(
    station_name: str,
    start: Optional[datetime] = Query(None, description="Start datetime (ISO-8601)"),
    end: Optional[datetime] = Query(None, description="End datetime (ISO-8601)"),
    limit: int = Query(100, ge=1, le=5000, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
):
    """
    Paginated access to raw sensor readings.
    Optionally filter by **start** and **end** datetime.
    """
    df = load_master()

    mask = df["station_name"].str.lower() == station_name.lower()
    station_df = df[mask].sort_values("time")

    if station_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{station_name}' not found.",
        )

    if start:
        station_df = station_df[station_df["time"] >= pd.Timestamp(start)]
    if end:
        station_df = station_df[station_df["time"] <= pd.Timestamp(end)]

    total = len(station_df)
    page_df = station_df.iloc[offset : offset + limit]

    return {
        "station_name": station_name,
        "total_records": total,
        "offset": offset,
        "limit": limit,
        "returned": len(page_df),
        "readings": _dataframe_to_readings(page_df),
    }


# Private helpers
# Sensor columns we expose — must match SensorReading schema fields
def _dataframe_to_readings(df: pd.DataFrame) -> List[SensorReading]:
    """Convert a DataFrame slice into a list of SensorReading Pydantic models."""
    readings = []
    available = [c for c in SENSOR_COLS if c in df.columns]
    for _, row in df[available].iterrows():
        data = {col: _nan_to_none(row.get(col)) for col in available}
        readings.append(SensorReading(**data))
    return readings


def _nan_to_none(value):
    """Convert NaN / NaT to None so Pydantic serialises it as null."""
    if pd.isna(value):
        return None
    return value


# Dev entrypoint — run with Ctrl+Shift+F5 in VS Code
if __name__ == "__main__":
    print("Station list (first 3) ")
    result = get_stations()
    for s in result[:3]:
        print(s.model_dump())

    print("\nMonthly data — BapujiNagar Jan 2025 (first 2 readings) ")
    monthly = get_monthly_data("BapujiNagar", year=2025, month=1)
    print(f"Total readings: {monthly.total_readings}")
    for r in monthly.readings[:2]:
        print(r.model_dump())
