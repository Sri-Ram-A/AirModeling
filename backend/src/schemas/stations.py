"""
backend/schemas.py
Pydantic models for request validation and response serialisation.
Keeping all schemas in one file makes them easy to find and import.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Station schemas
class Station(BaseModel):
    """Core station identity fields."""

    name: str
    latitude: float
    longitude: float
    site_id: Optional[int] 
    organization: Optional[str] 

SENSOR_COLS = [
    "time",
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
    "average_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "rainfall",
    "total_rainfall",
    "solar_radiation",
    "pressure",
]

# Sensor / time-series schemas
class SensorReading(BaseModel):
    """One 15-minute reading for a single station."""

    time: datetime
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no: Optional[float] = None
    no2: Optional[float] = None
    nox: Optional[float] = None
    nh3: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    benzene: Optional[float] = None
    toluene: Optional[float] = None
    average_temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    rainfall: Optional[float] = None
    total_rainfall: Optional[float] = None
    solar_radiation: Optional[float] = None
    pressure: Optional[float] = None


class MonthlyStationData(BaseModel):
    """Response for the monthly station data endpoint."""

    station_name: str
    year: int
    month: int
    total_readings: int
    readings: List[SensorReading]


