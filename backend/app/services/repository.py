# app/services/repository.py

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

from app.config import Settings, get_settings


@dataclass(frozen=True)
class Snapshot:
    """One timestamp worth of station dataframe."""

    timestamp: pd.Timestamp
    dataframe: pd.DataFrame


class DataRepository:
    """Data access layer for station metadata and time-indexed observations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.stations_df = pd.read_csv(self.settings.stations_file)
        self.master_df = pd.read_csv(
            self.settings.master_dataset_file, parse_dates=["time"]
        )
        self._validate_df()
        self.station_names = (
            self.stations_df["StationName"].dropna().astype(str).tolist()
        )
        self.station_lookup = self.stations_df.set_index("StationName")

    def _validate_df(self) -> None:
        """Validate the expected dataframe columns at load time."""
        station_required = {"StationName", "Latitude", "Longitude"}
        master_required = {"time", "station_name"}
        missing_station = station_required - set(self.stations_df.columns)
        missing_master = master_required - set(self.master_df.columns)
        if missing_station:
            raise ValueError(
                f"stations_file is missing columns: {sorted(missing_station)}"
            )
        if missing_master:
            raise ValueError(
                f"master_dataset_file is missing columns: {sorted(missing_master)}"
            )

    @property
    def station_count(self) -> int:
        """Total number of configured stations."""
        return len(self.station_names)

    @property
    def available_columns(self) -> list[str]:
        """All columns available in the master dataset."""
        return self.master_df.columns.tolist()

    def get_station_metadata(self) -> pd.DataFrame:
        """Return a copy of the station metadata dataframe."""
        return self.stations_df.copy()

    def _station_scope(self) -> pd.DataFrame:
        """Return master dataframe restricted to configured stations."""
        return self.master_df[
            self.master_df["station_name"].isin(self.station_names)
        ].copy()

    def get_timestamp_snapshot(self, timestamp: str) -> Snapshot:
        """Return all station dataframe for an exact timestamp.

        Args:
            timestamp: ISO 8601 timestamp.

        Returns:
            Snapshot containing the timestamp and matching dataframe.

        Raises:
            ValueError: If no dataframe exist for the requested timestamp.
        """
        ts = pd.to_datetime(timestamp)
        dataframe = self._station_scope()
        dataframe = dataframe[dataframe["time"] == ts].copy()
        if dataframe.empty:
            raise ValueError(f"No data available for timestamp: {timestamp}")
        return Snapshot(timestamp=ts, dataframe=dataframe)

    def get_latest_snapshot(self) -> Snapshot:
        """Return the latest timestamp available in the dataset."""
        scoped = self._station_scope()
        if scoped.empty:
            raise ValueError("No station data available.")
        ts = scoped["time"].max()
        dataframe = scoped[scoped["time"] == ts].copy()
        if dataframe.empty:
            raise ValueError("Unable to locate the latest snapshot.")
        return Snapshot(timestamp=pd.Timestamp(ts), dataframe=dataframe)

    def get_latest_snapshot_required_columns(
        self,
        required_columns: list[str],
        min_station_count: int,
    ) -> Snapshot:
        """Return the latest timestamp with enough usable station rows.
        A station row is considered usable only if all columns in
        `required_columns` are non-null.

        Args:
            required_columns: Columns that must be present for a row to count as usable.
            min_station_count: Minimum number of usable station rows required for a timestamp.

        Returns:
            Snapshot for the latest qualifying timestamp.

        Raises:
            ValueError: If no station data is available.
        """
        scoped = self._station_scope()
        if scoped.empty:
            raise ValueError("No station data available.")

        if not required_columns:
            raise ValueError("required_columns must not be empty.")

        usable = scoped.dropna(subset=required_columns)
        coverage = usable.groupby("time")["station_name"].nunique()
        valid_times = coverage[coverage >= min_station_count]

        if valid_times.empty:
            return self.get_latest_snapshot()

        ts = valid_times.index.max()
        dataframe = scoped[scoped["time"] == ts].copy()
        if dataframe.empty:
            raise ValueError("Unable to locate a usable snapshot.")
        return Snapshot(timestamp=pd.Timestamp(ts), dataframe=dataframe)

    def align_columns(
        self, snapshot: Snapshot, columns: list[str]
    ) -> dict[str, np.ndarray]:
        """Align selected columns to the canonical station order.

        Missing stations are filled with NaN.

        Args:
            snapshot: Snapshot to align.
            columns: Column names to extract.

        Returns:
            Mapping of column name to station-aligned numpy array.
        """
        indexed = snapshot.dataframe.set_index("station_name").reindex(
            self.station_names
        )
        aligned: dict[str, np.ndarray] = {}

        for column in columns:
            if column in indexed.columns:
                values = pd.to_numeric(indexed[column], errors="coerce").to_numpy(
                    dtype=float
                )
            else:
                values = np.full(self.station_count, np.nan, dtype=float)
            aligned[column] = values
        return aligned

    def station_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """Return station coordinates in canonical station order."""
        meta = self.station_lookup.reindex(self.station_names)
        latitudes = pd.to_numeric(meta["Latitude"], errors="coerce").to_numpy(
            dtype=float
        )
        longitudes = pd.to_numeric(meta["Longitude"], errors="coerce").to_numpy(
            dtype=float
        )
        return latitudes, longitudes
