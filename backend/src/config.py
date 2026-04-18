"""
src/config.py
Centralised configuration — paths, constants, defaults.
All other modules import from here so there is a single source of truth.
"""

from pathlib import Path

# Directory layout
ROOT_DIR: Path = Path(__file__).resolve().parents[2]   # project root
BACKEND_DIR: Path = ROOT_DIR / "backend"
DATA_DIR: Path = BACKEND_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"


# Key file paths
STATIONS_CSV: Path = RAW_DIR / "stations.csv"
MASTER_CSV: Path = ARTIFACTS_DIR / "master_dataset.csv"
IMPUTED_CSV: Path = ARTIFACTS_DIR / "final_master_dataset.csv"
STATIONS_MAP_HTML: Path = ARTIFACTS_DIR / "stations_map.html"


# Gaussian plume defaults
DEFAULT_STACK_HEIGHT_M: float = 20.0       # effective stack height (metres)
DEFAULT_WIND_SPEED_MS: float = 2.0         # fallback wind speed  (m/s)
DEFAULT_WIND_DIRECTION_DEG: float = 180.0  # fallback wind direction (degrees)
DEFAULT_SOLAR_RADIATION_WM2: float = 300.0 # fallback solar radiation (W/m²)


# Imputation gap thresholds (in 15-min intervals)
MAX_GAP_INTERPOLATION: int = 24    # < 6 hours
MAX_GAP_PREVIOUS_DAY: int = 192    # < 48 hours
MAX_GAP_PREVIOUS_WEEK: int = 672   # < 7 days

# Private helpers
def _require_file(path: Path) -> Path:
    """Raise a clear error if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {path}\n"
            "Check your DATA_DIR configuration in backend/config.py"
        )
    return path
