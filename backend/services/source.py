# backend/services/source.py
import pandas as pd
from loguru import logger
from typing import List
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from .location import LocationService


@dataclass
class Source:
    """Represents a pollution source (initially just nearby stations)"""

    name: str
    latitude: float
    longitude: float
    source_type: str  # e.g., "station", "industrial", "traffic"

    def __repr__(self):
        return f"Source({self.name}, type={self.source_type})"


class SourceService:
    """
    Identifies and manages pollution sources.
    Currently simplified: uses nearby monitoring stations as proxy sources.
    """

    def __init__(self, master_dataset_path: Path, stations_csv_path: Path):
        """
        Initialize with master dataset and station metadata
        Args:
            master_dataset_path: Path to master_dataset.csv
            stations_csv_path: Path to stations.csv
        """
        self.master_df = pd.read_csv(master_dataset_path)
        self.master_df["time"] = pd.to_datetime(self.master_df["time"])
        logger.info(f"Loaded {len(self.master_df)} records from master dataset")
        self.location_service = LocationService(stations_csv_path)
        self.sources: List[Source] = []

    def identify_sources_from_stations(
        self, target_station_name: str, top_k: int = 5
    ) -> List[Source]:
        """
        Use nearby monitoring stations as proxy sources
        Args:
            target_station_name: Name of target station (e.g., "RVCE-Mailasandra")
            top_k: Number of nearest stations to use as sources
        Returns:
            List of Source objects
        """
        logger.info(f"Identifying top {top_k} sources for {target_station_name}")

        # Get target station coordinates
        target_station = self.location_service.get_station_by_name(target_station_name)
        logger.info(
            f"Target station: {target_station.name} at ({target_station.latitude}, {target_station.longitude})"
        )

        # Find nearest stations
        nearest = self.location_service.find_nearest_stations(
            target_station.latitude, target_station.longitude, k=top_k
        )

        # Convert to Source objects (excluding the target station itself if it appears)
        sources = []
        for station, distance in nearest:
            if station.name != target_station.name:
                source = Source(
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    source_type="monitoring_station",
                )
                sources.append(source)
                logger.debug(f"Added source: {source.name} at {distance:.2f} km")

        # If we don't have enough sources, add some dummy industrial sources
        if len(sources) < top_k:
            logger.warning(f"Only found {len(sources)} unique sources, need {top_k}")
            # You could add industrial area coordinates here

        self.sources = sources
        logger.success(f"Identified {len(sources)} sources")

        return sources

    def get_source_data_for_time(
        self, source_names: List[str], target_time: datetime
    ) -> pd.DataFrame:
        """
        Retrieve pollutant data for given sources at specific time
        Args:
            source_names: List of source station names
            target_time: Timestamp to query

        Returns:
            DataFrame with source emissions data
        """
        logger.info(f"Retrieving data for {len(source_names)} sources at {target_time}")

        # Filter master dataset for target time and source stations
        mask = (self.master_df["time"] == target_time) & (
            self.master_df["station_name"].isin(source_names)
        )

        source_data = self.master_df[mask].copy()

        if source_data.empty:
            logger.error(f"No data found for sources at {target_time}")
            raise ValueError("No data available for the specified time")

        logger.success(f"Retrieved data for {len(source_data)} stations")
        logger.debug(f"Available pollutants: {source_data.columns.tolist()}")

        return source_data


# Example usage:
if __name__ == "__main__":
    # Configure logger
    logger.add(lambda msg: print(msg), level="INFO")

    # Setup paths
    ROOT_DIR = Path().cwd()
    MASTER_PATH = ROOT_DIR / "backend" / "data" / "artifacts" / "master_dataset.csv"
    STATIONS_PATH = ROOT_DIR / "backend" / "data" / "raw" / "stations.csv"

    # Initialize service
    source_service = SourceService(MASTER_PATH, STATIONS_PATH)

    # Identify sources for RVCE
    sources = source_service.identify_sources_from_stations(
        target_station_name="RVCE-Mailasandra", top_k=5
    )

    print("\n" + "=" * 50)
    print("IDENTIFIED SOURCES")
    print("=" * 50)
    for i, source in enumerate(sources, 1):
        print(f"{i}. {source.name} (type: {source.source_type})")

    # Get data for a specific time
    test_time = pd.to_datetime("2025-01-01 00:00:00")
    source_names = [s.name for s in sources]

    try:
        data = source_service.get_source_data_for_time(source_names, test_time)
        print(f"\nData retrieved for {test_time}:")
        print(
            data[
                ["station_name", "pm25", "pm10", "wind_speed", "wind_direction"]
            ].to_string()
        )
    except ValueError as e:
        print(f"Error: {e}")
