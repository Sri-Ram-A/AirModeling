from __future__ import annotations

import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

import app.data as data
from app.inversion import compute_inversion
from app.schemas import InversionResponse

router = APIRouter(prefix="/inversion", tags=["inversion"])


@router.get(
    "/invert_snapshot",
    response_model=InversionResponse,
    summary="Source inversion for one snapshot",
    description=(
        "Solves C = T·Q using four classical methods and returns contribution matrices "
        "instead of the raw transport matrix."
    ),
)
def invert_snapshot(
    pollutant: str = Query(..., description="Pollutant column, e.g. pm25, no2."),
    timestamp: str | None = Query(
        default=None,
        description="ISO-8601 timestamp. Omit for the latest usable snapshot.",
    ),
) -> InversionResponse:
    # 1. Validate the pollutant presence in the dataset and raise 422 if invalid.
    try:
        data.validate_pollutant(pollutant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 2. Parse timestamp if provided.
    ts: pd.Timestamp | None = pd.to_datetime(timestamp) if timestamp else None

    # 3. Fetch the snapshot.
    snap: pd.DataFrame = data.get_snapshot(timestamp=ts, columns=[pollutant])
    if snap.empty:
        raise HTTPException(
            status_code=404,
            detail="No data available for the selected snapshot.",
        )

    # 4. Resolve the actual timestamp used by the data layer.
    snapshot_ts = pd.to_datetime(snap["time"].iloc[0])

    # 5. Align required columns to canonical station order.
    vectors = data.align_to_stations(
        snap,
        ["wind_speed", "wind_direction", "solar_radiation", pollutant],
    )

    # 6. Impute missing values in the backend layer.
    observed = np.asarray(data.impute_median(vectors[pollutant]), dtype=float)
    wind_speed = np.asarray(data.impute_median(vectors["wind_speed"]), dtype=float)
    wind_dir = np.asarray(data.impute_median(vectors["wind_direction"]), dtype=float)
    solar_rad = np.asarray(data.impute_median(vectors["solar_radiation"]), dtype=float)

    # 7. Load station coordinates in canonical order.
    lats, lons = data.station_coordinates()
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)

    # 8. Run pure inversion logic.
    try:
        result = compute_inversion(
            timestamp=str(snapshot_ts),
            pollutant=pollutant,
            station_names=list(data.STATION_NAMES),
            lats=lats,
            lons=lons,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
            solar_radiation=solar_rad,
            observed_concentration=observed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 9. Log the computation result.
    logger.info(
        "Inversion complete | ts={} | pollutant={} | stations={}",
        result.timestamp,
        result.pollutant,
        len(result.station_names),
    )

    # 10. Return the fully formed response.
    return result
