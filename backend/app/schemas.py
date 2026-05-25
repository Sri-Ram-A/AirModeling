from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class StationMeta(BaseModel):
    """Static metadata for one monitoring station."""

    station_name: str = Field(..., description="Unique station identifier.")
    latitude: float = Field(..., description="Station latitude in decimal degrees.")
    longitude: float = Field(..., description="Station longitude in decimal degrees.")


class PollutantReadings(BaseModel):
    """Pollutant concentrations recorded at a station."""

    pm25: float | None = Field(default=None, description="PM2.5 concentration.")
    pm10: float | None = Field(default=None, description="PM10 concentration.")
    no: float | None = Field(default=None, description="NO concentration.")
    no2: float | None = Field(default=None, description="NO2 concentration.")
    nox: float | None = Field(default=None, description="NOx concentration.")
    nh3: float | None = Field(default=None, description="NH3 concentration.")
    so2: float | None = Field(default=None, description="SO2 concentration.")
    co: float | None = Field(default=None, description="CO concentration.")
    o3: float | None = Field(default=None, description="O3 concentration.")
    benzene: float | None = Field(default=None, description="Benzene concentration.")
    toluene: float | None = Field(default=None, description="Toluene concentration.")


class MeteorologyReadings(BaseModel):
    """Meteorological readings recorded at a station."""

    average_temperature: float | None = Field(
        default=None, description="Average air temperature."
    )
    relative_humidity: float | None = Field(
        default=None, description="Relative humidity."
    )
    wind_speed: float | None = Field(default=None, description="Wind speed in m/s.")
    wind_direction: float | None = Field(
        default=None, description="Wind direction in degrees."
    )
    rainfall: float | None = Field(default=None, description="Rainfall amount.")
    total_rainfall: float | None = Field(
        default=None, description="Cumulative rainfall."
    )
    solar_radiation: float | None = Field(
        default=None, description="Solar radiation in W/m²."
    )
    pressure: float | None = Field(default=None, description="Atmospheric pressure.")


class StationSnapshot(StationMeta):
    """All data returned for one station in a single snapshot."""

    pollutants: PollutantReadings = Field(..., description="Pollutant values.")
    meteorology: MeteorologyReadings = Field(..., description="Meteorological values.")


class CurrentReadingResponse(BaseModel):
    """Represents the API response schema for a multi-station data snapshot.

    This model serves as the top-level payload envelope, capturing aggregate
    metrics, selection metadata, and a collection of synchronized readings
    across all active monitoring stations for a specific point in time.

    Attributes:
        timestamp (str): The ISO-8601 or formatted string timestamp.
        total_stations (int): The total count of monitoring stations.
        stations_in_snapshot (int): The actual number of stations that successfully reported valid data for this specific timestamp.
        selected_pollutant (str): The target chemical compound or particulate matter
            (e.g., 'PM2.5', 'NO2') utilized as the filtering key to determine
            the most complete/usable data snapshot.
        readings (list[StationSnapshot]): A validated array of individual station
            payloads containing metadata, pollutants, and meteorological data,
            sorted strictly in the system's canonical station sequence.
    """

    timestamp: str = Field(..., description="Selected snapshot timestamp.")
    total_stations: int = Field(..., description="Total configured stations.")
    stations_in_snapshot: int = Field(
        ..., description="Stations with data in snapshot."
    )
    selected_pollutant: str = Field(
        ..., description="Pollutant used to choose the usable snapshot."
    )
    readings: list[StationSnapshot] = Field(
        ..., description="Station snapshots in canonical station order."
    )


class TransportMatrixResponse(BaseModel):
    """Transport matrix response for one snapshot.
    ### Attributes:
    - **timestamp**: Selected snapshot timestamp.
    - **pollutant**: Pollutant used as observed input.
    - **station_names**: Station names in matrix order.
    - **stability_classes**: Pasquill stability class per source station.
    - **transport_matrix**: Square transport matrix T where C = T · Q.
    - **current_reading**: Observed concentration vector C in station order.
    """

    timestamp: str = Field(..., description="Selected snapshot timestamp.")
    pollutant: str = Field(..., description="Pollutant used as observed input.")
    station_names: list[str] = Field(..., description="Station names in matrix order.")
    stability_classes: list[str] = Field(
        ..., description="Pasquill stability class computed per source station."
    )
    transport_matrix: list[list[float]] = Field(
        ..., description="Square transport matrix T where C = T · Q."
    )
    current_reading: list[float] = Field(
        ..., description="Observed concentration vector C in station order."
    )


class SolverMethod(str, Enum):
    """Available inversion solvers.
    ### Attributes:
    - **lstsq** : Ordinary least-squares solver.
    - **nnls** : Non-negative least-squares solver.
    - **tikhonov** : Ridge-regularized solver.
    - **truncated_svd** : Truncated SVD solver.
    """

    lstsq = "lstsq"
    nnls = "nnls"
    tikhonov = "tikhonov"
    truncated_svd = "truncated_svd"


class ContributionResponse(BaseModel):
    """Emission attribution result for a given solver.
    ### Attributes:
    - **method** : Inversion method used.
    - **timestamp** : Snapshot timestamp.
    - **pollutant** : Pollutant used as observed input.
    - **residual_norm** : L2 norm of residual vector.
    - **rank** : Matrix rank if available.
    - **condition_number** : Condition number if available.
    - **observed_concentrations** : Observed concentration vector C.
    - **estimated_emissions** : Estimated emission vector Q.
    - **reconstructed_concentrations** : Reconstructed concentration vector T · Q.
    - **residuals** : Elementwise residuals C - T·Q.
    """

    method: SolverMethod = Field(..., description="Inversion method used.")
    timestamp: str = Field(..., description="Snapshot timestamp.")
    pollutant: str = Field(..., description="Pollutant used as observed input.")
    residual_norm: float = Field(..., description="L2 norm of residual vector.")
    rank: int | None = Field(None, description="Matrix rank if available.")
    condition_number: float | None = Field(
        None, description="Condition number if available."
    )
    observed_concentrations: list[float] = Field(
        ..., description="Observed concentration vector C."
    )
    estimated_emissions: list[float] = Field(
        ..., description="Estimated emission vector Q."
    )
    reconstructed_concentrations: list[float] = Field(
        ..., description="Reconstructed concentration vector T · Q."
    )
    residuals: list[float] = Field(..., description="Elementwise residuals C - T·Q.")


class HealthResponse(BaseModel):
    """Basic service health payload.
    ### Attributes:
    - **status** : Service status.
    - **app_name** : Application name.
    - **version** : Application version.
    """

    status: str = Field(..., description="Service status.")
    app_name: str = Field(..., description="Application name.")
    version: str = Field(..., description="Application version.")


class ErrorResponse(BaseModel):
    """Standard API error payload.
    ### Attributes:
    - **detail** : Error description.
    - **context** : Optional debug context.
    """

    detail: str = Field(..., description="Error description.")
    context: dict[str, Any] | None = Field(default=None, description="Debug context.")
