from __future__ import annotations

import pandas as pd

from app.config import Settings, get_settings
from app.schemas import (
    CurrentReadingResponse,
    MeteorologyReadings,
    PollutantReadings,
    StationSnapshot,
)
from app.services.repository import DataRepository, Snapshot


class ReadingService:
    """Build the current-reading API payload from a selected snapshot."""

    def __init__(
        self,
        repository: DataRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or DataRepository(self.settings)

    def current_reading(self, timestamp: str | None = None) -> CurrentReadingResponse:
        """Return the latest usable current-reading snapshot.

        Args:
            timestamp: Optional ISO 8601 timestamp. If omitted, the latest usable
                snapshot is selected automatically.

        Returns:
            CurrentReadingResponse with one entry per configured station.
        """
        # 1. Columns where NaN values are not acceptable
        required_columns = [
            self.settings.pollutant,
            "wind_speed",
            "wind_direction",
            "solar_radiation",
        ]
        
        # 2. Extract Snapshot (timestamp,dataframe) for latest or provided timestamp
        if timestamp is None:
            snapshot: Snapshot = self.repository.get_latest_snapshot_required_columns(
                required_columns=required_columns,
                min_station_count=self.settings.min_complete_stations,
            )
        else:
            snapshot: Snapshot = self.repository.get_timestamp_snapshot(timestamp)
        
        # 3. Return the Dataframe
        rows_by_station = snapshot.dataframe.set_index("station_name")
        station_rows: list[StationSnapshot] = []

        for station_name in self.repository.station_names:
            meta = self.repository.station_lookup.loc[station_name]
            row = (
                rows_by_station.loc[station_name]
                if station_name in rows_by_station.index
                else None
            )
            station_rows.append(self._build_station_snapshot(station_name, meta, row))

        stations_in_snapshot = int(
            rows_by_station.index.intersection(self.repository.station_names).size
        )

        return CurrentReadingResponse(
            timestamp=str(snapshot.timestamp),
            total_stations=self.repository.station_count,
            stations_in_snapshot=stations_in_snapshot,
            selected_pollutant=self.settings.pollutant,
            readings=station_rows,
        )

    def _build_station_snapshot(
        self,
        station_name: str,
        meta: pd.Series,
        row: pd.Series | None,
    ) -> StationSnapshot:
        """Build one station snapshot from metadata and an optional data row."""
        return StationSnapshot(
            station_name=station_name,
            latitude=self._to_float(meta.get("Latitude")),
            longitude=self._to_float(meta.get("Longitude")),
            pollutants=PollutantReadings(
                pm25=self._row_float(row, "pm25"),
                pm10=self._row_float(row, "pm10"),
                no=self._row_float(row, "no"),
                no2=self._row_float(row, "no2"),
                nox=self._row_float(row, "nox"),
                nh3=self._row_float(row, "nh3"),
                so2=self._row_float(row, "so2"),
                co=self._row_float(row, "co"),
                o3=self._row_float(row, "o3"),
                benzene=self._row_float(row, "benzene"),
                toluene=self._row_float(row, "toluene"),
            ),
            meteorology=MeteorologyReadings(
                average_temperature=self._row_float(row, "average_temperature"),
                relative_humidity=self._row_float(row, "relative_humidity"),
                wind_speed=self._row_float(row, "wind_speed"),
                wind_direction=self._row_float(row, "wind_direction"),
                rainfall=self._row_float(row, "rainfall"),
                total_rainfall=self._row_float(row, "total_rainfall"),
                solar_radiation=self._row_float(row, "solar_radiation"),
                pressure=self._row_float(row, "pressure"),
            ),
        )

    @staticmethod
    def _row_float(row: pd.Series | None, column: str) -> float | None:
        """Convert a row value to float, preserving nulls."""
        if row is None:
            return None
        value = row.get(column)
        return ReadingService._to_float(value)

    @staticmethod
    def _to_float(value: object) -> float | None:
        """Convert a scalar to float, or return None for missing values."""
        if value is None or pd.isna(value):
            return None
        return float(value)


def get_reading_service() -> ReadingService:
    """Dependency provider for the current-reading service."""
    return ReadingService()
