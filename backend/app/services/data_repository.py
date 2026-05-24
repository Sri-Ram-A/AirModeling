from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

from app.config import Settings, get_settings


@dataclass(frozen=True)
class Snapshot:
    timestamp: pd.Timestamp
    current: pd.DataFrame


class DataRepository:
    """Loads station metadata and extracts aligned snapshots."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.stations_df = pd.read_csv(self.settings.stations_file)
        self.master_df = pd.read_csv(
            self.settings.master_dataset_file, parse_dates=["time"]
        )
        self.station_names = self.stations_df["StationName"].dropna().tolist()
        self.station_lookup = self.stations_df.set_index("StationName")

    def get_station_meta(self) -> pd.DataFrame:
        return self.stations_df.copy()

    def _filtered(self) -> pd.DataFrame:
        df = self.master_df[self.master_df["station_name"].isin(self.station_names)]
        cols = [
            self.settings.pollutant,
            "wind_speed",
            "wind_direction",
            "solar_radiation",
        ]
        return df.dropna(subset=cols)

    def snapshot_for_time(self, timestamp: str | None) -> Snapshot:
        df = self._filtered()

        if timestamp is not None:
            ts = pd.to_datetime(timestamp)
            snap = df[df["time"] == ts]
            if snap.empty:
                raise ValueError(f"No data available for timestamp: {timestamp}")
            return Snapshot(timestamp=ts, current=snap.copy())

        pivot = df.pivot_table(
            index="time",
            columns="station_name",
            values=self.settings.pollutant,
            aggfunc="first",
        )
        complete = pivot.dropna(axis=0, thresh=self.settings.min_complete_stations)

        if complete.empty:
            ts = df["time"].max()
        else:
            ts = complete.index.max()

        snap = df[df["time"] == ts]
        if snap.empty:
            raise ValueError("Unable to locate a usable snapshot.")
        return Snapshot(timestamp=pd.Timestamp(ts), current=snap.copy())

    def aligned_vectors(
        self, snapshot: Snapshot
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return pollutant, wind speed, wind direction and solar arrays."""
        snap = snapshot.current.set_index("station_name")
        pollutant = []
        wind_speed = []
        wind_direction = []
        solar_radiation = []

        for name in self.station_names:
            if name in snap.index:
                row = snap.loc[name]
                pollutant.append(float(row[self.settings.pollutant]))
                wind_speed.append(float(row["wind_speed"]))
                wind_direction.append(float(row["wind_direction"]))
                solar_radiation.append(float(row["solar_radiation"]))
            else:
                pollutant.append(np.nan)
                wind_speed.append(np.nan)
                wind_direction.append(np.nan)
                solar_radiation.append(np.nan)

        return (
            np.asarray(pollutant, dtype=float),
            np.asarray(wind_speed, dtype=float),
            np.asarray(wind_direction, dtype=float),
            np.asarray(solar_radiation, dtype=float),
        )

    def station_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        return (
            self.stations_df["Latitude"].astype(float).to_numpy(),
            self.stations_df["Longitude"].astype(float).to_numpy(),
        )

    @staticmethod
    def impute_median(values: np.ndarray) -> np.ndarray:
        if np.isfinite(values).any():
            fill_value = np.nanmedian(values)
            return np.where(np.isnan(values), fill_value, values)
        return np.zeros_like(values)
