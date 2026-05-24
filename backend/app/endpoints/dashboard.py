from __future__ import annotations
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import (
    ContributionResponse,
    CurrentReadingResponse,
    SolverMethod,
    StationMeta,
    TransportMatrixResponse,
)
from app.services.inversion import InversionService

router = APIRouter()


@lru_cache
def get_service() -> InversionService:
    return InversionService()


@router.get(
    "/current_reading",
    response_model=CurrentReadingResponse,
    summary="Get current station readings",
    description=(
        "Returns the latest complete 15-minute snapshot for all stations, or a "
        "specific timestamp if provided."
    ),
)
def get_current_reading(
    timestamp: str | None = Query(
        default=None,
        description="Optional ISO timestamp. If omitted, the latest usable snapshot is used.",
    ),
    service: InversionService = Depends(get_service),
) -> CurrentReadingResponse:
    try:
        return CurrentReadingResponse(**service.current_reading(timestamp))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/get_transport_matrix",
    response_model=TransportMatrixResponse,
    summary="Build the transport matrix",
    description=(
        "Converts the current station readings into an NxN Gaussian plume transport "
        "matrix. Each column represents a source station and each row a receptor station."
    ),
)
def get_transport_matrix(
    timestamp: str | None = Query(
        default=None,
        description="Optional ISO timestamp. If omitted, the latest usable snapshot is used.",
    ),
    service: InversionService = Depends(get_service),
) -> TransportMatrixResponse:
    try:
        payload = service.transport_matrix(timestamp)
        return TransportMatrixResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/get_contributions/{method}",
    response_model=ContributionResponse,
    summary="Invert the transport matrix",
    description=(
        "Solves C = T · Q using the chosen inversion method and returns the estimated "
        "emission vector together with reconstruction diagnostics."
    ),
)
def get_contributions(
    method: SolverMethod,
    timestamp: str | None = Query(
        default=None,
        description="Optional ISO timestamp. If omitted, the latest usable snapshot is used.",
    ),
    service: InversionService = Depends(get_service),
) -> ContributionResponse:
    try:
        payload = service.solve(method, timestamp)
        return ContributionResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/stations",
    response_model=list[StationMeta],
    summary="List stations",
    description="Returns the station metadata used by the dashboard and inversion engine.",
)
def list_stations(
    service: InversionService = Depends(get_service),
) -> list[StationMeta]:
    return [
        StationMeta(**row)
        for row in service.repository.get_station_meta().to_dict(orient="records")
    ]
