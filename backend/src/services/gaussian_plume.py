"""
src/services/transport_matrix.py
### Calculates transport coefficients (T matrix) for Gaussian plume dispersion model.
- Converts source emissions to predicted concentrations at receptor locations.
- The wind blows the pollution downwind, creating a plume that spreads out like a cone.
- The concentration of pollution is highest at the centerline and decreases in a bell-shaped (Gaussian) pattern as you move sideways (crosswind) or up/down (vertical).
    C = (Q / (2π x u x sigma_y x sigma_z)) x exp(-y²/(2sigma_y²)) x exp(-(z-H)²/(2sigma_z²))
    C = concentration at receptor (kg/m³)
    Q = emission rate from source (kg/s)
    u = wind speed (m/s)
    sigma_y, sigma_z = how much the plume spreads horizontally/vertically
    H = effective stack height (m)
"""

from geopy.distance import distance
from geopy.point import Point
from loguru import logger
from typing import Tuple, Optional
import math
from pydantic import BaseModel


class StabilityCoefficients(BaseModel):
    """Pasquill-Gifford dispersion coefficients for each stability class"""

    a_y: float
    b_y: float
    a_z: float
    b_z: float


# Pasquill-Gifford coefficients lookup table
STABILITY_COEFFICIENTS = {
    "A": StabilityCoefficients(a_y=0.36, b_y=0.90, a_z=0.00023, b_z=2.10),
    "B": StabilityCoefficients(a_y=0.25, b_y=0.90, a_z=0.058, b_z=1.09),
    "C": StabilityCoefficients(a_y=0.19, b_y=0.90, a_z=0.11, b_z=0.91),
    "D": StabilityCoefficients(a_y=0.13, b_y=0.90, a_z=0.57, b_z=0.58),
    "E": StabilityCoefficients(a_y=0.096, b_y=0.90, a_z=0.85, b_z=0.47),
    "F": StabilityCoefficients(a_y=0.063, b_y=0.90, a_z=0.77, b_z=0.42),
}


class GaussianPlumeModel:
    """
    Gaussian plume dispersion model for calculating transport coefficients.
    Calculates T = concentration (µg/m³) per unit emission rate (g/s)
    from a source to a receptor based on:
    - Distance and direction between source and receptor
    - Wind speed and direction
    - Atmospheric stability
    - Effective stack height
    """

    # Initalize the stack height ("Starting height" of the plume)
    def __init__(self, stack_height: float = 20.0):
        """
        Initialize the Gaussian plume model.
        Args:
            stack_height: Effective stack height in meters (default 20m)
        """
        self.stack_height = stack_height

    # Calculates the compass direction from source to receptor.
    # To determine if the receptor is downwind or upwind of the source.
    def calculate_bearing(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate initial bearing (azimuth) from point1 to point2.
        Args:
            lat1, lon1: Coordinates of starting point (degrees)
            lat2, lon2: Coordinates of ending point (degrees)
        Returns:
            Bearing in degrees (0° = North, clockwise)
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)

        # Calculate bearing using atan2 formula
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
            lat2_rad
        ) * math.cos(delta_lon)

        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)
        # Normalize to 0-360 degrees
        bearing_deg = (bearing_deg + 360) % 360
        return bearing_deg

    # Calculates straight-line distance between two points on Earth.
    def calculate_distance_meters(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate great-circle distance between two points in meters.
        Args:
            lat1, lon1: Coordinates of first point (degrees)
            lat2, lon2: Coordinates of second point (degrees)
        Returns:
            Distance in meters
        """
        point1 = Point(lat1, lon1)
        point2 = Point(lat2, lon2)
        dist_km = distance(point1, point2).kilometers
        dist_m = dist_km * 1000
        return dist_m

    def calculate_downwind_crosswind(
        self, distance_m: float, bearing: float, wind_direction: float
    ) -> Tuple[float, float]:
        """
        Calculate downwind (x) and crosswind (y) distances.
        Args:
            distance_m: Straight-line distance from source to receptor (meters)
            bearing: Bearing from source to receptor (degrees, 0°=North)
            wind_direction: Wind direction (degrees, 0°=North, direction wind is FROM)
        Returns:
            Tuple of (x, y) where:
            - x: Downwind distance (meters, positive if receptor is downwind)
            - y: Crosswind distance (meters, positive to right of wind direction)
        """
        # Wind direction is where wind comes FROM
        # For plume travel, wind blows FROM wind_direction TO (wind_direction + 180)
        wind_blowing_to = (wind_direction + 180) % 360
        # Angle between wind direction and source-to-receptor line
        angle_diff = wind_blowing_to - bearing
        # Convert to radians
        angle_rad = math.radians(angle_diff)
        # Calculate downwind and crosswind components
        x = distance_m * math.cos(angle_rad)  # Downwind distance
        y = distance_m * math.sin(angle_rad)  # Crosswind distance
        return x, y

    # Determines how turbulent the atmosphere is (affects plume spreading).
    def calculate_stability_class(
        self,
        wind_speed: float,
        solar_radiation: Optional[float] = None,
        time_of_day: Optional[str] = None,
    ) -> str:
        """
        Determine Pasquill-Gifford atmospheric stability class.
        Args:
            wind_speed: Wind speed in m/s
            solar_radiation: Solar radiation in W/m² (if available)
            time_of_day: 'day', 'night', or None (will use solar_radiation to determine)
        Returns:
            Stability class: 'A', 'B', 'C', 'D', 'E', or 'F'
        """
        # Determine day/night based on solar radiation or time
        if solar_radiation is not None:
            if solar_radiation > 400:
                insolation = "strong"
            elif solar_radiation > 200:
                insolation = "moderate"
            elif solar_radiation > 50:
                insolation = "weak"
            else:
                insolation = "night"
        else:
            insolation = "neutral" if time_of_day == "day" else "night"

        # Pasquill stability class determination
        if insolation == "strong":
            if wind_speed < 2:
                return "A"
            elif wind_speed < 3:
                return "A"
            elif wind_speed < 5:
                return "B"
            else:
                return "C"

        elif insolation == "moderate":
            if wind_speed < 2:
                return "A"
            elif wind_speed < 3:
                return "B"
            elif wind_speed < 5:
                return "B"
            else:
                return "C"

        elif insolation == "weak":
            if wind_speed < 2:
                return "B"
            elif wind_speed < 3:
                return "C"
            elif wind_speed < 5:
                return "C"
            else:
                return "D"

        elif insolation == "night":
            if wind_speed < 2:
                return "F"
            elif wind_speed < 3:
                return "E"
            elif wind_speed < 5:
                return "D"
            else:
                return "D"

        else:  # neutral / overcast
            return "D"

    # Calculates σ_y and σ_z - how wide and tall the plume becomes.
    def calculate_dispersion_coefficients(
        self, x: float, stability_class: str
    ) -> Tuple[float, float]:
        """
        Calculate sigma_y and sigma_z using Pasquill-Gifford formulas.
        Args:
            x: Downwind distance in meters
            stability_class: 'A' through 'F'
        Returns:
            Tuple of (sigma_y, sigma_z) in meters
        """
        if x <= 0:
            logger.debug(f"x={x} <= 0, returning zero dispersion")
            return 0.0, 0.0

        coeff = STABILITY_COEFFICIENTS.get(stability_class)
        if not coeff:
            logger.warning(
                f"Unknown stability class: {stability_class}, using D (neutral)"
            )
            coeff = STABILITY_COEFFICIENTS["D"]

        sigma_y = coeff.a_y * (x**coeff.b_y)
        sigma_z = coeff.a_z * (x**coeff.b_z)

        return sigma_y, sigma_z

    # Claculate Transport Coefficient
    def calculate_transport_coefficient(
        self,
        source_lat: float,
        source_lon: float,
        target_lat: float,
        target_lon: float,
        wind_speed: float,
        wind_direction: float,
        stability_class: str | None = None,
        solar_radiation: float | None = None,
        time_of_day: str | None = None,
    ) -> float:
        """
        Calculate transport coefficient T for a single source-receptor pair.
        T = concentration (µg/m³) per unit emission rate (g/s)
        Args:
            source_lat, source_lon: Source coordinates (degrees)
            target_lat, target_lon: Target coordinates (degrees)
            wind_speed: Wind speed in m/s
            wind_direction: Wind direction in degrees (0°=North, direction wind is FROM)
            stability_class: Optional pre-determined stability class
            solar_radiation: Solar radiation in W/m² (for stability calculation)
            time_of_day: 'day' or 'night' (for stability calculation)
        Returns:
            Transport coefficient T in (µg/m³)/(g/s)
        """
        # Step 1: Calculate distance and bearing
        distance_m = self.calculate_distance_meters(
            source_lat, source_lon, target_lat, target_lon
        )
        bearing = self.calculate_bearing(source_lat, source_lon, target_lat, target_lon)
        # Step 2: Calculate downwind and crosswind distances
        x, y = self.calculate_downwind_crosswind(distance_m, bearing, wind_direction)
        # If receptor is upwind, no contribution
        if x <= 0:
            logger.debug(f"Receptor is upwind (x={x:.1f}m). T = 0")
            return 0.0
        # Step 3: Determine stability class if not provided
        if stability_class is None:
            stability_class = self.calculate_stability_class(
                wind_speed, solar_radiation, time_of_day
            )
        # Step 4: Calculate dispersion coefficients
        sigma_y, sigma_z = self.calculate_dispersion_coefficients(x, stability_class)
        if sigma_y <= 0 or sigma_z <= 0:
            logger.warning(
                f"Invalid dispersion coefficients: sigma_y={sigma_y}, sigma_z={sigma_z}"
            )
            return 0.0
        # Step 5: Apply Gaussian plume formula for ground-level receptor (z=0)
        # Formula: T = (1 / (π × u × σ_y × σ_z)) × exp(-y²/(2σ_y²)) × exp(-H²/(2σ_z²))
        # Term 1: 1 / (π × u × σ_y × σ_z)
        denominator = math.pi * wind_speed * sigma_y * sigma_z
        if denominator <= 0:
            logger.warning(f"Invalid denominator: {denominator}")
            return 0.0
        term1 = 1.0 / denominator
        # Term 2: exp(-y²/(2σ_y²))
        if sigma_y > 0:
            term2 = math.exp(-(y * y) / (2 * sigma_y * sigma_y))
        else:
            term2 = 0.0
        # Term 3: exp(-H²/(2σ_z²))
        if sigma_z > 0:
            term3 = math.exp(
                -(self.stack_height * self.stack_height) / (2 * sigma_z * sigma_z)
            )
        else:
            term3 = 0.0
        # Transport coefficient in (g/m³)/(g/s) = s/m³
        T = term1 * term2 * term3
        # Convert to (µg/m³)/(g/s) by multiplying by 1,000,000
        T_actual = T * 1_000_000
        return T_actual

