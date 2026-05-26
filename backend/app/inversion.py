from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from scipy.linalg import lstsq, svd
from scipy.optimize import nnls

from app.schemas import InversionResponse, MatrixDiagnostics, SolverResult


# 1. Physical constants and Pasquill-Gifford coefficients
# Pasquill-Gifford stability coefficients (Turner, 1970)
# Classes A (very unstable) → F (stable)
PG_COEFFS: dict[str, dict[str, float]] = {
    "A": dict(a_y=0.36, b_y=0.90, a_z=0.00023, b_z=2.10),
    "B": dict(a_y=0.25, b_y=0.90, a_z=0.058, b_z=1.09),
    "C": dict(a_y=0.19, b_y=0.90, a_z=0.11, b_z=0.91),
    "D": dict(a_y=0.13, b_y=0.90, a_z=0.57, b_z=0.58),
    "E": dict(a_y=0.096, b_y=0.90, a_z=0.85, b_z=0.47),
    "F": dict(a_y=0.063, b_y=0.90, a_z=0.77, b_z=0.42),
}

MIN_WIND_SPEED_MS = 0.5
MAX_SIGMA_Z_M = 500.0
H_STACK_M = 20.0


# 2. Geometry helpers
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    1. Great-circle distance between two lat/lon points in kilometres.
    """
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return float(2 * R * np.arcsin(np.sqrt(a)))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    1. Initial bearing from point 1 to point 2, clockwise from North.
    """
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    theta = np.arctan2(
        np.sin(dlambda) * np.cos(phi2),
        np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda),
    )
    return float(np.degrees(theta) % 360)


# 3. Timestamp helpers
def _parse_hour(timestamp: str) -> int:
    """
    1. Parse an ISO-like timestamp string and return the hour.
    2. Accepts timestamps with a trailing Z as well.
    """
    try:
        ts = timestamp.strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).hour
    except Exception as exc:
        raise ValueError(f"Invalid timestamp: {timestamp}") from exc


# 4. Meteorology helpers
def _stability_class(wind_speed_ms: float, solar_rad_wm2: float, is_daytime: bool) -> str:
    """
    1. Approximate Pasquill stability class from wind speed and solar radiation.
    2. This is a simplified Turner-style lookup.
    """
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
    else:
        if u < 2:
            return "F"
        if u < 3:
            return "E"
        return "D"


# 5. Gaussian plume transport coefficient
def _transport_element(
    lat_src: float,
    lon_src: float,
    lat_rec: float,
    lon_rec: float,
    wind_speed_ms: float,
    wind_dir_deg: float,
    stability_cls: str,
    h_stack_m: float = H_STACK_M,
) -> float:
    """
    1. Transport coefficient T[i, j].
    2. Returns concentration at receptor i due to a unit emission from source j.
    3. Unit: µg/m³ per g/s
    """
    # 1. Reject invalid meteorology immediately.
    if not np.isfinite(wind_speed_ms) or not np.isfinite(wind_dir_deg):
        return 0.0

    # 2. Apply minimum wind floor for numerical stability.
    u = max(float(wind_speed_ms), MIN_WIND_SPEED_MS)

    # 3. Compute source→receptor distance.
    d_km = _haversine_km(lat_src, lon_src, lat_rec, lon_rec)
    d_km = max(d_km, 0.1)
    d_m = d_km * 1_000.0

    # 4. Compute source→receptor bearing.
    bearing = _bearing_deg(lat_src, lon_src, lat_rec, lon_rec)

    # 5. Convert to downwind / crosswind coordinates.
    delta_rad = np.radians(wind_dir_deg - bearing)
    x_m = d_m * np.cos(delta_rad)
    y_m = d_m * np.sin(delta_rad)

    # 6. Upwind receptor contributes nothing.
    if x_m <= 0 or not np.isfinite(x_m) or not np.isfinite(y_m):
        return 0.0

    # 7. Pasquill-Gifford dispersion coefficients.
    c = PG_COEFFS[stability_cls]
    sigma_y = c["a_y"] * x_m ** c["b_y"]
    sigma_z = min(c["a_z"] * x_m ** c["b_z"], MAX_SIGMA_Z_M)

    if sigma_y < 1e-6 or sigma_z < 1e-6:
        return 0.0

    # 8. Ground-level Gaussian plume with image-source reflection.
    lateral = np.exp(-(y_m**2) / (2.0 * sigma_y**2))
    vertical = np.exp(-(h_stack_m**2) / (2.0 * sigma_z**2))
    t_raw = (1.0 / (np.pi * u * sigma_y * sigma_z)) * lateral * vertical

    if not np.isfinite(t_raw):
        return 0.0

    # 9. Convert g/s -> µg/m³ per g/s.
    return float(t_raw * 1e6)


# 6. Matrix construction
def build_transport_matrix(
    timestamp: str,
    lats: np.ndarray,
    lons: np.ndarray,
    wind_speed: np.ndarray,
    wind_direction: np.ndarray,
    solar_radiation: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    """
    1. Build the N×N Gaussian plume transport matrix.
    2. No backend logic here.
    3. No data loading here.
    """
    # 1. Validate lengths.
    n = len(lats)
    if n < 2:
        raise ValueError("At least two stations are required for inversion.")
    if not (
        len(lons) == len(wind_speed) == len(wind_direction) == len(solar_radiation) == n
    ):
        raise ValueError("All input vectors must have the same length.")

    # 2. Resolve day/night classification from timestamp.
    hour = _parse_hour(timestamp)
    is_day = 6 <= hour <= 18

    # 3. Compute one stability class per source station.
    stability_classes = [
        _stability_class(float(wind_speed[j]), float(solar_radiation[j]), is_day)
        for j in range(n)
    ]

    # 4. Fill T[i, j] = transport from source j to receptor i.
    T = np.zeros((n, n), dtype=float)
    for j in range(n):
        for i in range(n):
            T[i, j] = _transport_element(
                lat_src=float(lats[j]),
                lon_src=float(lons[j]),
                lat_rec=float(lats[i]),
                lon_rec=float(lons[i]),
                wind_speed_ms=float(wind_speed[j]),
                wind_dir_deg=float(wind_direction[j]),
                stability_cls=stability_classes[j],
            )

    return T, stability_classes


# 7. Solver helpers
def _contribution_matrix(T: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """
    1. Build the source contribution matrix.
    2. Entry [i][j] = T[i][j] * Q[j].
    3. Row sums reproduce the modeled concentration at receptor i.
    """
    return T * Q[np.newaxis, :]


def _solver_result(
    method: str,
    T: np.ndarray,
    C_obs: np.ndarray,
    Q: np.ndarray,
    metadata: dict[str, Any] | None = None,
) -> SolverResult:
    """
    1. Assemble one solver output.
    """
    C_hat = T @ Q
    residuals = C_obs - C_hat
    contribution = _contribution_matrix(T, Q)

    return SolverResult(
        method=method,
        residual_norm=float(np.linalg.norm(residuals)),
        Q=Q.tolist(),
        reconstructed_C=C_hat.tolist(),
        residuals=residuals.tolist(),
        contribution_matrix=contribution.tolist(),
        negative_q_count=int((Q < 0).sum()),
        metadata=metadata,
    )


def solve_all_methods(
    T: np.ndarray,
    C_obs: np.ndarray,
) -> tuple[list[SolverResult], MatrixDiagnostics]:
    """
    1. Solve C = T·Q using classical methods.
    2. Return solver outputs plus shared diagnostics.
    """
    # 1. Least squares.
    Q_lstsq, _, _, sv = lstsq(T, C_obs)
    Q_lstsq = np.asarray(Q_lstsq, dtype=float)

    # 2. Non-negative least squares.
    Q_nnls, _ = nnls(T, C_obs)
    Q_nnls = np.asarray(Q_nnls, dtype=float)

    # 3. Tikhonov regularisation.
    lam = 0.1
    Q_tikh = np.linalg.solve(T.T @ T + lam * np.eye(T.shape[1]), T.T @ C_obs)

    # 4. Truncated SVD.
    U, s, Vt = svd(T, full_matrices=False)
    threshold = 1e-3 * s[0]
    s_inv = np.where(s > threshold, 1.0 / s, 0.0)
    Q_svd = Vt.T @ (s_inv * (U.T @ C_obs))

    # 5. Shared diagnostics.
    cond = float(s[0] / s[-1]) if s[-1] > 0 else None
    diagnostics = MatrixDiagnostics(
        shape=list(T.shape),
        rank=int(np.linalg.matrix_rank(T)),
        condition_number=cond,
        singular_values=s.tolist(),
    )

    # 6. Pack results in a stable order.
    solutions = [
        _solver_result("lstsq", T, C_obs, Q_lstsq),
        _solver_result("nnls", T, C_obs, Q_nnls),
        _solver_result("tikhonov", T, C_obs, Q_tikh, metadata={"lambda": lam}),
        _solver_result(
            "truncated_svd",
            T,
            C_obs,
            Q_svd,
            metadata={"threshold": float(threshold)},
        ),
    ]

    return solutions, diagnostics


# 8. High-level public API
def compute_inversion(
    timestamp: str,
    pollutant: str,
    station_names: list[str],
    lats: np.ndarray,
    lons: np.ndarray,
    wind_speed: np.ndarray,
    wind_direction: np.ndarray,
    solar_radiation: np.ndarray,
    observed_concentration: np.ndarray,
) -> InversionResponse:
    """
    1. Pure computation entrypoint.
    2. The backend prepares arrays and passes them here.
    3. This returns the final API response model.
    """
    # 1. Build transport matrix and stability classes.
    T, stability_classes = build_transport_matrix(
        timestamp=timestamp,
        lats=lats,
        lons=lons,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        solar_radiation=solar_radiation,
    )

    # 2. Solve the inverse problem.
    solutions, diagnostics = solve_all_methods(T, observed_concentration)

    # 3. Assemble final response.
    return InversionResponse(
        timestamp=timestamp,
        pollutant=pollutant,
        station_names=station_names,
        stability_classes=stability_classes,
        observed_concentrations=observed_concentration.tolist(),
        solutions=solutions,
        diagnostics=diagnostics,
    )