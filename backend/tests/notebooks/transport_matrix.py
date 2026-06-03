
"""
transport_matrix.py

Reusable Gaussian-plume transport matrix utilities extracted from the notebook.
"""

import numpy as np

H_STACK = 20.0

PG_COEFFS = {
    "A": dict(a_y=0.36, b_y=0.90, a_z=0.00023, b_z=2.10),
    "B": dict(a_y=0.25, b_y=0.90, a_z=0.058, b_z=1.09),
    "C": dict(a_y=0.19, b_y=0.90, a_z=0.11, b_z=0.91),
    "D": dict(a_y=0.13, b_y=0.90, a_z=0.57, b_z=0.58),
    "E": dict(a_y=0.096, b_y=0.90, a_z=0.85, b_z=0.47),
    "F": dict(a_y=0.063, b_y=0.90, a_z=0.77, b_z=0.42),
}

MIN_WIND_SPEED_MS = 0.5
MAX_SIGMA_Z_M = 500.0


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    theta = np.arctan2(
        np.sin(dlambda) * np.cos(phi2),
        np.cos(phi1) * np.sin(phi2)
        - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda),
    )
    return np.degrees(theta) % 360


def stability_class(wind_speed_ms, solar_rad_Wm2, is_daytime):
    u = wind_speed_ms
    sr = solar_rad_Wm2

    if is_daytime:
        if u < 2:
            return "A" if sr > 600 else ("B" if sr > 300 else "C")
        elif u < 3:
            return "B" if sr > 300 else "C"
        elif u < 5:
            return "C" if sr > 50 else "D"
        else:
            return "D"
    else:
        if u < 2:
            return "F"
        elif u < 3:
            return "E"
        else:
            return "D"


def sigma_y_z(x_m, cls):
    c = PG_COEFFS[cls]
    sigma_y = c["a_y"] * x_m ** c["b_y"]
    sigma_z = min(c["a_z"] * x_m ** c["b_z"], MAX_SIGMA_Z_M)
    return sigma_y, sigma_z


def transport_element(
    lat_src,
    lon_src,
    lat_rec,
    lon_rec,
    wind_speed_ms,
    wind_dir_deg,
    stability_cls,
    H_m=H_STACK,
):
    if not np.isfinite(wind_speed_ms) or not np.isfinite(wind_dir_deg):
        return 0.0

    u = max(float(wind_speed_ms), MIN_WIND_SPEED_MS)

    d_km = haversine_km(lat_src, lon_src, lat_rec, lon_rec)

    if d_km < 0.01:
        d_km = 0.1

    d_m = d_km * 1000.0

    bearing = bearing_deg(lat_src, lon_src, lat_rec, lon_rec)

    delta_rad = np.radians(wind_dir_deg - bearing)

    x_m = d_m * np.cos(delta_rad)
    y_m = d_m * np.sin(delta_rad)

    if x_m <= 0:
        return 0.0

    sigma_y, sigma_z = sigma_y_z(x_m, stability_cls)

    if sigma_y < 1e-6 or sigma_z < 1e-6:
        return 0.0

    lateral = np.exp(-(y_m**2) / (2 * sigma_y**2))
    vertical = np.exp(-(H_m**2) / (2 * sigma_z**2))

    T_raw = (1.0 / (np.pi * u * sigma_y * sigma_z)) * lateral * vertical

    if not np.isfinite(T_raw):
        return 0.0

    return T_raw * 1e6


def build_transport_matrix(
    lats,
    lons,
    wind_speeds,
    wind_directions,
    stability_classes,
    stack_height=H_STACK,
):
    """
    Returns NxN transport matrix.

    Rows    = receptors
    Columns = sources
    """
    n = len(lats)
    T = np.zeros((n, n))

    for j in range(n):  # source
        for i in range(n):  # receptor
            T[i, j] = transport_element(
                lats[j],
                lons[j],
                lats[i],
                lons[i],
                wind_speeds[j],
                wind_directions[j],
                stability_classes[j],
                stack_height,
            )

    return T