from collections import Counter

import numpy as np
import pandas as pd
from scipy.linalg import lstsq, svd
from scipy.optimize import nnls

import app.data as data
from app.schemas import (
    MatrixDiagnostics,
    SolverResult,
)

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
# Physical constants
MIN_WIND_SPEED_MS = 0.5  # PG equations break down below this
MAX_SIGMA_Z_M = 500.0  # cap vertical dispersion for numerical stability
H_STACK_M = 20.0  # effective emission height [m]


# Pure geometry / physics helpers
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points [km]."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 → point 2, clockwise from North [°]."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    theta = np.arctan2(
        np.sin(dlambda) * np.cos(phi2),
        np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda),
    )
    return float(np.degrees(theta) % 360)


def _stability_class(
    wind_speed_ms: float, solar_rad_wm2: float, is_daytime: bool
) -> str:
    """
    Pasquill stability class (A-F) from wind speed, solar radiation and time of day.
    Simplified lookup from Turner (1970).
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
    Gaussian plume transport coefficient T[i,j]:
    concentration at receptor i due to a 1 g/s emission at source j.

    Returns 0.0 for:
      - Invalid / non-finite meteorology
      - Upwind receptor (x ≤ 0 in downwind coordinates)
      - Numerically degenerate dispersion coefficients

    Output unit: µg/m³ per g/s
    """
    # 1. Reject bad met data early.
    if not np.isfinite(wind_speed_ms) or not np.isfinite(wind_dir_deg):
        return 0.0

    # 2. Apply minimum wind speed floor (PG equations singular at u → 0).
    u = max(float(wind_speed_ms), MIN_WIND_SPEED_MS)

    # 3. Great-circle distance source → receptor [m].
    d_km = _haversine_km(lat_src, lon_src, lat_rec, lon_rec)
    d_km = max(d_km, 0.1)  # same-station diagonal: use 100 m to stay well-defined
    d_m = d_km * 1_000.0

    # 4. Bearing from source to receptor [°N clockwise].
    bearing = _bearing_deg(lat_src, lon_src, lat_rec, lon_rec)

    # 5. Decompose into downwind (x) and crosswind (y) coordinates.
    #    x > 0 means the receptor is downwind of the source.
    delta_rad = np.radians(wind_dir_deg - bearing)
    x_m = d_m * np.cos(delta_rad)
    y_m = d_m * np.sin(delta_rad)

    # 6. Receptor is upwind - no contribution.
    if x_m <= 0 or not np.isfinite(x_m) or not np.isfinite(y_m):
        return 0.0

    # 7. Pasquill-Gifford dispersion parameters.
    c = PG_COEFFS[stability_cls]
    sigma_y = c["a_y"] * x_m ** c["b_y"]
    sigma_z = min(c["a_z"] * x_m ** c["b_z"], MAX_SIGMA_Z_M)

    if sigma_y < 1e-6 or sigma_z < 1e-6:
        return 0.0

    # 8. Ground-level Gaussian plume (with image-source ground reflection).
    lateral = np.exp(-(y_m**2) / (2.0 * sigma_y**2))
    vertical = np.exp(-(h_stack_m**2) / (2.0 * sigma_z**2))
    T_raw = (1.0 / (np.pi * u * sigma_y * sigma_z)) * lateral * vertical

    if not np.isfinite(T_raw):
        return 0.0

    # 9. Convert g/s → µg/m³ per g/s.
    return float(T_raw * 1e6)


# Core computation: build T and solve for Q
def _build_transport_matrix(
    wind_speed: np.ndarray,
    wind_dir: np.ndarray,
    solar_rad: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    hour: int,
) -> tuple[np.ndarray, list[str]]:
    """
    Build the N×N Gaussian plume transport matrix T.

    Returns
    -------
    T               : ndarray shape (N, N)
    stability_classes : list of N stability class strings
    """
    N = len(data.STATION_NAMES)
    is_day = 6 <= hour <= 18

    # 1. Compute one stability class per source station.
    stability_classes = [
        _stability_class(wind_speed[j], solar_rad[j], is_day) for j in range(N)
    ]

    # 2. Fill T[i, j] = transport from source j to receptor i.
    T = np.zeros((N, N), dtype=float)
    for j in range(N):
        for i in range(N):
            T[i, j] = _transport_element(
                lat_src=lats[j],
                lon_src=lons[j],
                lat_rec=lats[i],
                lon_rec=lons[i],
                wind_speed_ms=wind_speed[j],
                wind_dir_deg=wind_dir[j],
                stability_cls=stability_classes[j],
            )

    return T, stability_classes


def _solve_all_methods(
    T: np.ndarray,
    C_obs: np.ndarray,
) -> tuple[list[SolverResult], MatrixDiagnostics]:
    """
    Solve C = T·Q using four classical methods.

    Methods
    -------
    1. lstsq          - minimum-norm least squares (scipy)
    2. nnls           - non-negative least squares (no negative emissions)
    3. tikhonov       - ridge regularisation  Q̂ = (TᵀT + λI)⁻¹ Tᵀ C
    4. truncated_svd  - pseudoinverse with small singular values zeroed out

    Returns
    -------
    solutions   : one SolverResult per method
    diagnostics : shared matrix diagnostics
    """
    # --- 1. Least squares ---
    Q_lstsq, _, rank_lstsq, sv = lstsq(T, C_obs)
    C_hat_lstsq = T @ Q_lstsq

    # --- 2. Non-negative least squares ---
    Q_nnls, _ = nnls(T, C_obs)
    C_hat_nnls = T @ Q_nnls

    # --- 3. Tikhonov (λ = 0.1) ---
    lam = 0.1
    Q_tikh = np.linalg.solve(T.T @ T + lam * np.eye(T.shape[1]), T.T @ C_obs)
    C_hat_tikh = T @ Q_tikh

    # --- 4. Truncated SVD ---
    U, s, Vt = svd(T, full_matrices=False)
    threshold = 1e-3 * s[0]
    s_inv = np.where(s > threshold, 1.0 / s, 0.0)
    Q_svd = Vt.T @ (s_inv * (U.T @ C_obs))
    C_hat_svd = T @ Q_svd

    # --- Shared matrix diagnostics ---
    cond = float(s[0] / s[-1]) if s[-1] > 0 else None
    diagnostics = MatrixDiagnostics(
        shape=list(T.shape),
        rank=int(np.linalg.matrix_rank(T)),
        condition_number=cond,
        singular_values=sv.tolist(),
    )

    def _result(method, Q, C_hat, rank=None, meta=None) -> SolverResult:
        residuals = C_obs - C_hat
        return SolverResult(
            method=method,
            residual_norm=float(np.linalg.norm(residuals)),
            Q=Q.tolist(),
            reconstructed_C=C_hat.tolist(),
            residuals=residuals.tolist(),
            negative_q_count=int((Q < 0).sum()),
            metadata=meta,
        )

    solutions = [
        _result("lstsq", Q_lstsq, C_hat_lstsq),
        _result("nnls", Q_nnls, C_hat_nnls),
        _result("tikhonov", Q_tikh, C_hat_tikh, meta={"lambda": lam}),
        _result(
            "truncated_svd", Q_svd, C_hat_svd, meta={"threshold": float(threshold)}
        ),
    ]

    return solutions, diagnostics


# Shared snapshot → (T, C_obs, meta) pipeline used by both endpoints
def _snapshot_to_matrix(
    pollutant: str,
    timestamp: pd.Timestamp | None,
) -> tuple[np.ndarray, np.ndarray, pd.Timestamp, list[str]]:
    """
    Load snapshot, impute met, build T.

    Returns
    -------
    T                 : transport matrix
    C_obs             : observed concentration vector
    snapshot_ts       : the actual timestamp used
    stability_classes : per-station stability class
    """
    # 1. Fetch snapshot rows from the global DataFrame.
    snap = data.get_snapshot(timestamp=timestamp, columns=[pollutant])
    if snap.empty:
        raise ValueError("No data available for the selected snapshot.")

    # 2. Extract the resolved timestamp.
    snapshot_ts: pd.Timestamp = pd.to_datetime(snap["time"].iloc[0])

    # 3. Align all required columns to canonical station order.
    vectors = data.align_to_stations(
        snap, ["wind_speed", "wind_direction", "solar_radiation", pollutant]
    )

    # 4. Impute missing values with column medians.
    C_obs = data.impute_median(vectors[pollutant])
    wind_speed = data.impute_median(vectors["wind_speed"])
    wind_dir = data.impute_median(vectors["wind_direction"])
    solar_rad = data.impute_median(vectors["solar_radiation"])

    # 5. Load station coordinates in canonical order.
    lats, lons = data.station_coordinates()

    # 6. Build the transport matrix.
    T, stability_classes = _build_transport_matrix(
        wind_speed=wind_speed,
        wind_dir=wind_dir,
        solar_rad=solar_rad,
        lats=lats,
        lons=lons,
        hour=snapshot_ts.hour,
    )
    return T, C_obs, snapshot_ts, stability_classes

