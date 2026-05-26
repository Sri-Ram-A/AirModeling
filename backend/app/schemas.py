# app/schemas.py

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# Dashboard schemas
class StationRow(BaseModel):
    """One observation row returned by dashboard endpoints."""

    model_config = ConfigDict(extra="ignore")

    time: str = Field(description="Observation timestamp (ISO-8601).")
    station_name: str = Field(description="Station identifier.")
    latitude: float | None = None
    longitude: float | None = None
    site: str | int | None = None
    org: str | None = None

    # Pollutants
    pm25: float | None = None
    pm10: float | None = None
    no: float | None = None
    no2: float | None = None
    nox: float | None = None
    nh3: float | None = None
    so2: float | None = None
    co: float | None = None
    o3: float | None = None
    benzene: float | None = None
    toluene: float | None = None

    # Meteorology
    average_temperature: float | None = None
    relative_humidity: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    rainfall: float | None = None
    total_rainfall: float | None = None
    solar_radiation: float | None = None
    pressure: float | None = None


# Inversion schemas
class SolverResult(BaseModel):
    """Emission estimates from one inversion method."""

    method: str = Field(description="Solver name.")
    residual_norm: float = Field(description="||C - T·Q||₂")
    Q: list[float] = Field(description="Emission vector [g/s].")
    reconstructed_C: list[float] = Field(
        description="T·Q reconstructed concentrations."
    )
    residuals: list[float] = Field(description="C - T·Q per station.")
    negative_q_count: int = Field(description="Stations with Q < 0.")
    metadata: dict[str, Any] | None = None


class MatrixDiagnostics(BaseModel):
    """SVD diagnostics for the transport matrix."""

    shape: list[int] = Field(description="[rows, cols]")
    rank: int
    condition_number: float | None = None
    singular_values: list[float]


class InversionResponse(BaseModel):
    """Full inversion result for one snapshot."""

    timestamp: str
    pollutant: str
    station_names: list[str]
    stability_classes: list[str]
    observed_concentrations: list[float]
    solutions: list[SolverResult]
    diagnostics: MatrixDiagnostics


class TransportMatrixResponse(BaseModel):
    """Raw transport matrix for one snapshot."""

    timestamp: str
    pollutant: str
    station_names: list[str]
    stability_classes: list[str]
    transport_matrix: list[list[float]]
    observed_concentrations: list[float]
