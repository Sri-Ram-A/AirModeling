# app/endpoints/inversion.py
"""
Inversion endpoints.

Gaussian plume transport matrix construction and source inversion (C = T·Q)
live directly in this file.  No service layer.  Logic mirrors the original
research notebook so it is easy to cross-reference.

References
----------
- Seinfeld & Pandis, "Atmospheric Chemistry and Physics", 3rd ed., 2016
- Pasquill & Smith, "Atmospheric Diffusion", 3rd ed., 1983
- Turner, EPA Workbook of Atmospheric Dispersion Estimates, 1970
"""

from __future__ import annotations


import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
import app.data as data
from app.schemas import (
    InversionResponse,
    TransportMatrixResponse,
)
from app.inversion import _snapshot_to_matrix, _solve_all_methods

router = APIRouter(prefix="/inversion", tags=["inversion"])


# GET /inversion/transport_matrix
@router.get(
    "/transport_matrix",
    response_model=TransportMatrixResponse,
    summary="Build the Gaussian plume transport matrix",
    description=(
        "Constructs the NxN transport matrix T for a single snapshot. "
        "T[i,j] is the concentration at station i due to a unit emission at station j."
    ),
)
def get_transport_matrix(
    pollutant: str = Query(..., description="Pollutant column (e.g. pm25, no2)."),
    timestamp: str | None = Query(
        default=None,
        description="ISO-8601 timestamp. Omit for the latest usable snapshot.",
    ),
) -> TransportMatrixResponse:
    # 1. Validate pollutant.
    try:
        data.validate_pollutant(pollutant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # 2. Parse timestamp.
    ts: pd.Timestamp | None = pd.to_datetime(timestamp) if timestamp else None
    # 3. Build transport matrix.
    try:
        T, C_obs, snapshot_ts, stability_classes = _snapshot_to_matrix(pollutant, ts)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TransportMatrixResponse(
        timestamp=str(snapshot_ts),
        pollutant=pollutant,
        station_names=data.STATION_NAMES,
        stability_classes=stability_classes,
        transport_matrix=T.tolist(),
        observed_concentrations=C_obs.tolist(),
    )


# GET /inversion/invert_snapshot
@router.get(
    "/invert_snapshot",
    response_model=InversionResponse,
    summary="Source inversion for one snapshot",
    description=(
        "Solves C = T·Q for a single snapshot using four classical methods: "
        "least squares, NNLS, Tikhonov regularisation, and truncated SVD."
    ),
)
def invert_snapshot(
    pollutant: str = Query(..., description="Pollutant column (e.g. pm25, no2)."),
    timestamp: str | None = Query(
        default=None,
        description="ISO-8601 timestamp. Omit for the latest usable snapshot.",
    ),
) -> InversionResponse:
    # 1. Validate pollutant.
    try:
        data.validate_pollutant(pollutant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # 2. Parse timestamp.
    ts: pd.Timestamp | None = pd.to_datetime(timestamp) if timestamp else None
    # 3. Build transport matrix and get C_obs.
    try:
        T, C_obs, snapshot_ts, stability_classes = _snapshot_to_matrix(pollutant, ts)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # 4. Solve C = T·Q using all four classical methods.
    solutions, diagnostics = _solve_all_methods(T, C_obs)
    logger.info(
        f"Inversion complete | ts={snapshot_ts} | pollutant={pollutant} "
        f"| methods={[s.method for s in solutions]}"
    )
    return InversionResponse(
        timestamp=str(snapshot_ts),
        pollutant=pollutant,
        station_names=data.STATION_NAMES,
        stability_classes=stability_classes,
        observed_concentrations=C_obs.tolist(),
        solutions=solutions,
        diagnostics=diagnostics,
    )

