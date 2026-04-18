from datetime import datetime
from pydantic import BaseModel, Field

class MatrixRequest(BaseModel):
    timestamp: datetime
    top_k: int = Field(5, ge=1)
    stack_height_m: float = Field(20.0, ge=0.0)


class NonZeroEntry(BaseModel):
    target: str
    source: str
    T: float
    target_idx: int
    source_idx: int


class MatrixResponse(BaseModel):
    timestamp: datetime
    top_k: int
    stack_height_m: float
    station_names: list[str]
    matrix_shape: list[int]
    nonzero_entries: list[NonZeroEntry]
    raw_matrix: list[list[float]]