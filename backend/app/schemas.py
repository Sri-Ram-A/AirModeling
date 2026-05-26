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


class SolverResult(BaseModel):
    """
    1. Output from one classical solver.
    2. Contribution matrix is included so the caller sees source→receptor impacts.
    """

    method: str = Field(description="Solver name.")
    residual_norm: float = Field(description="||C - T·Q||₂")
    Q: list[float] = Field(description="Estimated emissions [g/s].")
    reconstructed_C: list[float] = Field(
        description="Row-sum of the contribution matrix for each receptor station."
    )
    residuals: list[float] = Field(description="C_obs - C_hat per station.")
    contribution_matrix: list[list[float]] = Field(
        description="Contribution matrix where entry [i][j] = T[i][j] * Q[j]."
    )
    negative_q_count: int = Field(description="Count of negative emission estimates.")
    metadata: dict[str, Any] | None = None


class MatrixDiagnostics(BaseModel):
    """
    1. Shared diagnostics for the transport matrix.
    """

    shape: list[int] = Field(description="[rows, cols]")
    rank: int = Field(description="Numerical rank of T.")
    condition_number: float | None = Field(
        default=None, description="Condition number κ(T)."
    )
    singular_values: list[float] = Field(description="Singular value spectrum.")


class InversionResponse(BaseModel):
    """
    1. Final API response.
    2. Note: this does NOT return the transport matrix directly.
    3. Instead, each solver result includes a contribution matrix.
    """

    timestamp: str
    pollutant: str
    station_names: list[str]
    stability_classes: list[str]
    observed_concentrations: list[float]
    solutions: list[SolverResult]
    diagnostics: MatrixDiagnostics
