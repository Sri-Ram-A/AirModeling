# backend/services/location.py
import numpy as np
import pandas as pd
from loguru import logger
from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path
from tqdm import tqdm


@dataclass
class Station:
    """Represents an air quality monitoring station"""

    name: str
    site_id: int
    org: str
    latitude: float
    longitude: float

    def __repr__(self):
        return (
            f"Station({self.name}, lat={self.latitude:.4f}, lon={self.longitude:.4f})"
        )


class LocationService:
    """Handles distance calculations and nearest station identification"""

    def __init__(self, stations_csv_path: Path):
        """
        Initialize with station metadata
        Args:
            stations_csv_path: Path to stations.csv file
        """
        self.stations_df = pd.read_csv(stations_csv_path)
        self.total_stations = len(self.stations_df)
        logger.debug(f"Loaded {self.total_stations} stations")
        # Convert to list of Station objects for easier handling
        self.stations = []
        for _, row in tqdm(
            self.stations_df.iterrows(),
            total=self.total_stations,
            desc="Loading Stations",
        ):
            station = Station(
                name=row["StationName"],
                site_id=row["SiteID"],
                org=row["Organization"],
                latitude=row["Latitude"],
                longitude=row["Longitude"],
            )
            self.stations.append(station)

    def haversine_distance(
        self, latitude1: float, longitude1: float, latitude2: float, longitude2: float
    ) -> float:
        """
        Calculatitudee great-circle distance between two points on Earth
        Args:
            latitude1, longitude1: First point coordinates in degrees
            latitude2, longitude2: Second point coordinates in degrees
        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth's radius in kilometers

        # Convert to radians
        latitude1_rad = np.radians(latitude1)
        longitude1_rad = np.radians(longitude1)
        latitude2_rad = np.radians(latitude2)
        longitude2_rad = np.radians(longitude2)

        # Haversine formula
        dlatitude = latitude2_rad - latitude1_rad
        dlongitude = longitude2_rad - longitude1_rad

        a = (
            np.sin(dlatitude / 2) ** 2
            + np.cos(latitude1_rad)
            * np.cos(latitude2_rad)
            * np.sin(dlongitude / 2) ** 2
        )
        c = 2 * np.arcsin(np.sqrt(a))

        distance = R * c
        return distance

    def find_nearest_stations(
        self, target_lat: float, target_lon: float, k: int = 5
    ) -> List[Tuple[Station, float]]:
        """
        Find k nearest stations to target location
        Args:
            target_lat: Target latitude
            target_lon: Target longitude
            k: Number of nearest stations to return

        Returns:
            List of tuples (Station, distance_in_km) sorted by distance
        """
        logger.info(
            f"Finding {k} nearest stations to ({target_lat:.4f}, {target_lon:.4f})"
        )
        # Calculate distances to all stations
        distances = []
        for station in tqdm(
            self.stations,
            total=self.total_stations,
            desc="Calculating haversine distance",
        ):
            dist = self.haversine_distance(
                target_lat, target_lon, station.latitude, station.longitude
            )
            distances.append((station, dist))

        # Sort by distance and return top k
        distances.sort(key=lambda x: x[1])
        top_k = distances[:k]
        return top_k

    def get_station_by_name(self, name: str) -> Station:
        """Get station by name (case-insensitive partial match)"""
        name_lower = name.lower()
        for station in self.stations:
            if name_lower in station.name.lower():
                logger.info(f"Found station: {station.name}")
                return station
        logger.error(f"Station not found with name containing '{name}'")
        raise ValueError(f"Station not found: {name}")


# Example usage in interactive mode:
if __name__ == "__main__":
    # Initialize service
    ROOT_DIR = Path().cwd()
    STATION_META_PATH = ROOT_DIR / "backend" / "data" / "raw" / "stations.csv"
    location_service = LocationService(STATION_META_PATH)
    # RVCE coordinates (RVCE-Mailasandra)
    RVCE_LAT = 12.921418
    RVCE_LON = 77.502466
    # Find top 5 nearest stations to RVCE
    nearest = location_service.find_nearest_stations(RVCE_LAT, RVCE_LON, k=5)
    logger.success("TOP 5 NEAREST STATIONS TO RVCE")
    for i, (station, dist) in enumerate(nearest, 1):
        print(f"{i}. {station.name:25s} | Distance: {dist:.2f} km")
