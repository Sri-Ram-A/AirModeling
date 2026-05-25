from __future__ import annotations

import numpy as np
from scipy.linalg import lstsq, svd
from scipy.optimize import nnls

from app.config import Settings, get_settings
from app.schemas import SolverMethod
from app.services.repository import DataRepository
from app.utils.math import bearing_deg, haversine_km


PG_COEFFS = {
    "A": dict(a_y=0.36, b_y=0.90, a_z=0.00023, b_z=2.10),
    "B": dict(a_y=0.25, b_y=0.90, a_z=0.058, b_z=1.09),
    "C": dict(a_y=0.19, b_y=0.90, a_z=0.11, b_z=0.91),
    "D": dict(a_y=0.13, b_y=0.90, a_z=0.57, b_z=0.58),
    "E": dict(a_y=0.096, b_y=0.90, a_z=0.85, b_z=0.47),
    "F": dict(a_y=0.063, b_y=0.90, a_z=0.77, b_z=0.42),
}


class InversionService:
    """Builds transport matrices and solves for emissions."""

    def __init__(
        self,
        repository: DataRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or DataRepository(self.settings)

    def stability_class(
        self,
        wind_speed_ms: float,
        solar_rad_wm2: float,
        is_daytime: bool,
    ) -> str:
        u = wind_speed_ms
        sr = solar_rad_wm2
        if is_daytime:
            if u < 2:
                return "A" if sr > 600 else ("B" if sr > 300 else "C")
            if u < 3:
                return "B" if sr > 300 else "C"
            if u < 5:
                return "C" if sr > 50 else "D"
            return "D"
        if u < 2:
            return "F"
        if u < 3:
            return "E"
        return "D"

    def sigma_y_z(self, x_m: float, cls: str) -> tuple[float, float]:
        coeff = PG_COEFFS[cls]
        sigma_y = coeff["a_y"] * x_m ** coeff["b_y"]
        sigma_z = min(coeff["a_z"] * x_m ** coeff["b_z"], self.settings.max_sigma_z_m)
        return sigma_y, sigma_z

    def transport_element(
        self,
        lat_src: float,
        lon_src: float,
        lat_rec: float,
        lon_rec: float,
        wind_speed_ms: float,
        wind_dir_deg: float,
        stability_cls: str,
    ) -> float:
        if not np.isfinite(wind_speed_ms) or not np.isfinite(wind_dir_deg):
            return 0.0

        u = max(float(wind_speed_ms), self.settings.min_wind_speed_ms)
        distance_km = haversine_km(lat_src, lon_src, lat_rec, lon_rec)
        if distance_km < 0.01:
            distance_km = 0.1

        distance_m = distance_km * 1000.0
        bearing = bearing_deg(lat_src, lon_src, lat_rec, lon_rec)
        delta = np.radians(wind_dir_deg - bearing)
        x_m = distance_m * np.cos(delta)
        y_m = distance_m * np.sin(delta)

        if x_m <= 0 or not np.isfinite(x_m) or not np.isfinite(y_m):
            return 0.0

        sigma_y, sigma_z = self.sigma_y_z(x_m, stability_cls)
        if sigma_y < self.settings.epsilon or sigma_z < self.settings.epsilon:
            return 0.0

        lateral = np.exp(-(y_m**2) / (2.0 * sigma_y**2))
        vertical = np.exp(-(self.settings.stack_height_m**2) / (2.0 * sigma_z**2))
        transport = (1.0 / (np.pi * u * sigma_y * sigma_z)) * lateral * vertical
        if not np.isfinite(transport):
            return 0.0
        return float(transport * 1e6)

    def transport_matrix(self, timestamp: str | None = None) -> dict:
        snapshot = self.repository.get_timestamp_snapshot(timestamp)
        pollutant, wind_speed, wind_direction, solar_radiation = (
            self.repository.aligned_vectors(snapshot)
        )
        pollutant = self.repository.impute_median(pollutant)
        wind_speed = self.repository.impute_median(wind_speed)
        wind_direction = self.repository.impute_median(wind_direction)
        solar_radiation = self.repository.impute_median(solar_radiation)
        lats, lons = self.repository.station_coordinates()

        is_day = 6 <= snapshot.timestamp.hour <= 18
        stability = [
            self.stability_class(wind_speed[i], solar_radiation[i], is_day)
            for i in range(len(self.repository.station_names))
        ]

        n = len(self.repository.station_names)
        matrix = np.zeros((n, n), dtype=float)
        for j in range(n):
            for i in range(n):
                matrix[i, j] = self.transport_element(
                    lats[j],
                    lons[j],
                    lats[i],
                    lons[i],
                    wind_speed[j],
                    wind_direction[j],
                    stability[j],
                )

        return {
            "timestamp": str(snapshot.timestamp),
            "pollutant": self.settings.pollutant,
            "station_names": self.repository.station_names,
            "stability_classes": stability,
            "transport_matrix": matrix.tolist(),
            "current_reading": pollutant.tolist(),
        }

    def solve(self, method: SolverMethod, timestamp: str | None = None) -> dict:
        matrix_payload = self.transport_matrix(timestamp)
        current = np.asarray(matrix_payload["current_reading"], dtype=float)
        matrix = np.asarray(matrix_payload["transport_matrix"], dtype=float)

        if method == SolverMethod.lstsq:
            q, _, _, singular_values = lstsq(matrix, current)
            rank = int(np.linalg.matrix_rank(matrix))
            condition = self._condition_number(singular_values)
        elif method == SolverMethod.nnls:
            q, _ = nnls(matrix, current)
            rank = int(np.linalg.matrix_rank(matrix))
            singular_values = np.linalg.svd(matrix, compute_uv=False)
            condition = self._condition_number(singular_values)
        elif method == SolverMethod.tikhonov:
            lam = 0.1
            eye = np.eye(matrix.shape[1])
            q = np.linalg.solve(matrix.T @ matrix + lam * eye, matrix.T @ current)
            rank = int(np.linalg.matrix_rank(matrix))
            singular_values = np.linalg.svd(matrix, compute_uv=False)
            condition = self._condition_number(singular_values)
        else:
            u, s, vt = svd(matrix, full_matrices=False)
            thresh = 1e-3 * s[0]
            s_inv = np.where(s > thresh, 1.0 / s, 0.0)
            q = vt.T @ (s_inv * (u.T @ current))
            rank = int(np.linalg.matrix_rank(matrix))
            condition = self._condition_number(s)

        reconstructed = matrix @ q
        residual_vector = current - reconstructed

        return {
            "method": method,
            "timestamp": matrix_payload["timestamp"],
            "pollutant": matrix_payload["pollutant"],
            "residual_norm": float(np.linalg.norm(residual_vector)),
            "rank": rank,
            "condition_number": condition,
            "observed_concentrations": current.tolist(),
            "estimated_emissions": q.tolist(),
            "reconstructed_concentrations": reconstructed.tolist(),
            "residuals": residual_vector.tolist(),
        }

    @staticmethod
    def _condition_number(singular_values: np.ndarray) -> float | None:
        if singular_values.size == 0:
            return None
        s_min = float(np.min(singular_values))
        if s_min <= 0:
            return None
        return float(np.max(singular_values) / s_min)
