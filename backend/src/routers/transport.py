"""
src/routers/transport.py
FastAPI endpoints for the Gaussian plume transport matrix.
POST /transport/matrix
    → Full NxN matrix for all stations at a given timestamp + top_k.
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
import numpy as np
from src.schemas.transport import MatrixRequest, MatrixResponse, NonZeroEntry
from src.services.transport_matrix import TransportMatrixBuilder
from src.services.gaussian_plume import GaussianPlumeModel


router = APIRouter()


@router.post("/matrix", response_model=MatrixResponse)
def compute_matrix(body: MatrixRequest) -> MatrixResponse:
    try:
        # Create model dynamically (respects stack height)
        model = GaussianPlumeModel(stack_height=body.stack_height_m)
        builder = TransportMatrixBuilder(model)
        T, names = builder.build_full_matrix(
            timestamp=body.timestamp,
            top_k=body.top_k,
        )
        T = np.nan_to_num(
            T,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Sparse extraction
    nonzero_entries = [
        NonZeroEntry(
            target=names[j],
            source=names[i],
            T=round(float(T[j, i]), 6),
            target_idx=j,
            source_idx=i,
        )
        for j in range(len(names))
        for i in range(len(names))
        if T[j, i] > 0
    ]

    logger.success(
        f"Matrix built | size={T.shape} | nonzero={len(nonzero_entries)}"
    )

    return MatrixResponse(
        timestamp=body.timestamp,
        top_k=body.top_k,
        stack_height_m=body.stack_height_m,
        station_names=names,
        matrix_shape=list(T.shape),
        nonzero_entries=nonzero_entries,
        raw_matrix=[[round(float(v), 6) for v in row] for row in T],
    )