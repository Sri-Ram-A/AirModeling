"""
src/services/transport_matrix.py
Builds a full N x N transport matrix (all stations  x  all stations).
For each target, only the top-k nearest source stations get a computed
Gaussian plume coefficient — all others are set to 0.
Matrix layout:
         Source_1  Source_2  ...  Source_N
Target_1   T_11      T_12         T_1N
Target_2   T_21      T_22         T_2N
  ...
Target_N   T_N1      T_N2         T_NN
"""

from __future__ import annotations

from datetime import datetime
import numpy as np
import pandas as pd
from tqdm import tqdm
from loguru import logger

from src.services.gaussian_plume import GaussianPlumeModel
from src.services.data_loader import load_stations, load_master


class TransportMatrixBuilder:
    def __init__(self, model: GaussianPlumeModel):
        self.gaussian_model = model
        self.stations_df = load_stations()
        self.master_df = load_master()

    def build_full_matrix(
        self,
        timestamp: datetime,
        top_k: int = 5,
    ) -> tuple[np.ndarray, list[str]]:

        names = self.stations_df["name"].tolist()
        n = len(names)
        T = np.zeros((n, n))

        # Precompute distances
        dist_matrix = self._pairwise_distances(self.stations_df)
        time_of_day = "day" if 6 <= timestamp.hour <= 18 else "night"
        logger.info(f"Building {n}x{n} matrix | top_k={top_k} | time={time_of_day}")

        for j in tqdm(range(n), desc="Targets"):
            target_name = names[j]

            # Weather lookup (inline, simple)
            df = self.master_df[
                self.master_df["station_name"].str.lower() == target_name.lower()
            ].copy()

            if df.empty:
                wind_speed = 2.0
                wind_direction = 180.0
                solar_radiation = None
            else:
                df["_diff"] = (df["time"] - pd.Timestamp(timestamp)).abs()
                row = df.loc[df["_diff"].idxmin()]

                # fallback to column median if NaN
                wind_speed = (
                    row["wind_speed"]
                    if pd.notna(row["wind_speed"])
                    else df["wind_speed"].median()
                )

                wind_direction = (
                    row["wind_direction"]
                    if pd.notna(row["wind_direction"])
                    else df["wind_direction"].median()
                )

                solar_radiation = (
                    row["solar_radiation"]
                    if pd.notna(row.get("solar_radiation"))
                    else None
                )
            # Top-k nearest sources
            dists = dist_matrix[j].copy()
            dists[j] = np.inf
            top_k_idx = np.argsort(dists)[:top_k]

            # Calaculate Transport Coefficicents for each sources-target
            for i in top_k_idx:
                T[j, i] = self.gaussian_model.calculate_transport_coefficient(
                    source_lat=self.stations_df.loc[i, "latitude"],  # type:ignore
                    source_lon=self.stations_df.loc[i, "longitude"],  # type:ignore
                    target_lat=self.stations_df.loc[j, "latitude"],  # type:ignore
                    target_lon=self.stations_df.loc[j, "longitude"],  # type:ignore
                    wind_speed=float(wind_speed),
                    wind_direction=float(wind_direction),
                    solar_radiation=float(solar_radiation)
                    if solar_radiation is not None
                    else None,
                    time_of_day=time_of_day,
                )
        return T, names

    def _pairwise_distances(self, df: pd.DataFrame) -> np.ndarray:
        lats = np.radians(df["latitude"].values)
        lons = np.radians(df["longitude"].values)
        n = len(df)
        R = 6_371_000
        dist = np.zeros((n, n))
        for i in range(n):
            dlat = lats - lats[i]
            dlon = lons - lons[i]
            a = (
                np.sin(dlat / 2) ** 2
                + np.cos(lats[i]) * np.cos(lats) * np.sin(dlon / 2) ** 2
            )
            dist[i] = R * 2 * np.arcsin(np.sqrt(a))
        return dist



# Dev entrypoint
if __name__ == "__main__":
    model = GaussianPlumeModel(stack_height=20)
    builder = TransportMatrixBuilder(model)
    timestamp = datetime(year=2025, month=1, day=1, hour=9, minute=0)
    top_k = 5
    stack_height_m = 20
    T = builder.build_full_matrix(
        timestamp=timestamp,
        top_k=top_k,
    )
    print(T)
