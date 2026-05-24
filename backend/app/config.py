from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal


class Settings(BaseModel):
    """Application configuration."""

    app_name: Literal["Air Dashboard API"] = "Air Dashboard API"
    app_version: Literal["1.0.0"] = "1.0.0"
    api_prefix: Literal["/api"] = "/api"
    data_dir: Path = Field(default=Path("data"))
    stations_file: Path = Field(default=Path("data/raw/stations.csv"))
    master_dataset_file: Path = Field(
        default=Path("data/artifacts/final_master_dataset.csv")
    )
    pollutant: str = "pm25"
    min_complete_stations: int = 12
    stack_height_m: float = 20.0
    min_wind_speed_ms: float = 0.5
    max_sigma_z_m: float = 500.0
    epsilon: float = 1e-12


@lru_cache
def get_settings() -> Settings:
    return Settings()
