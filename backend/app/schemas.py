from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class StationMeta(BaseModel):
    """Static metadata for a monitoring station.
        ### Attributes:
        - **station_name** : Unique station identifier.
        - **latitude** : Station latitude in decimal degrees.
        - **longitude** : Station longitude in decimal degrees.
    """

    station_name: str = Field(..., description="Unique station identifier.")
    latitude: float = Field(..., description="Station latitude in decimal degrees.")
    longitude: float = Field(..., description="Station longitude in decimal degrees.")


class StationReading(BaseModel):
    """Per-station snapshot readings.
        ### Attributes:
        - **station_name** : Unique station identifier.
        - **pollutant** : Observed pollutant concentration.
        - **wind_speed** : Wind speed in m/s.
        - **wind_direction** : Wind direction in degrees.
        - **solar_radiation** : Solar radiation in W/m².
        - **timestamp** : Timestamp of the snapshot.
    """

    station_name: str = Field(..., description="Unique station identifier.")
    pollutant: float = Field(..., description="Observed pollutant concentration.")
    wind_speed: float = Field(..., description="Wind speed in m/s.")
    wind_direction: float = Field(..., description="Wind direction in degrees.")
    solar_radiation: float = Field(..., description="Solar radiation in W/m².")
    timestamp: str = Field(..., description="Timestamp of the snapshot.")


class CurrentReadingResponse(BaseModel):
    """Current pollutant snapshot response.  
        ### Attributes:
        - **timestamp** : Selected snapshot timestamp.   
        - **pollutant** : Pollutant column used.  
        - **station_count** : Total stations.  
        - **complete_station_count** : Stations in snapshot.  
        - **readings** : Per-station readings.  
    """

    timestamp: str = Field(..., description="Selected snapshot timestamp.")
    pollutant: str = Field(..., description="Pollutant column used for reading.")
    station_count: int = Field(..., description="Total number of stations.")
    complete_station_count: int = Field(
        ..., description="Stations present in the selected snapshot."
    )
    readings: list[StationReading] = Field(
        ..., description="Per-station current readings in station order."
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
