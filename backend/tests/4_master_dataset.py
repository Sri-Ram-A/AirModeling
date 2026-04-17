from pathlib import Path
import pandas as pd
from tqdm import tqdm
import re
from loguru import logger
import Pandaspretty as pp

ROOT_DIR = Path(__name__).resolve().parent
DATASET_DIR = ROOT_DIR / "backend" / "data"
RAW_DIR = DATASET_DIR / "raw" / "2025"
STATION_META_PATH = DATASET_DIR / "raw" / "stations.csv"

# Original columns in the raw data files:
# Timestamp,PM2.5 (µg/m³),PM10 (µg/m³),NO (µg/m³),NO2 (µg/m³),NOx (ppb),
# NH3 (µg/m³),SO2 (µg/m³),CO (mg/m³),Ozone (µg/m³),Benzene (µg/m³),Toluene (µg/m³),
# Xylene (µg/m³),O Xylene (µg/m³),Eth-Benzene (µg/m³),MP-Xylene (µg/m³),
# AT (°C),RH (%),WS (m/s),WD (deg),RF (mm),TOT-RF (mm),SR (W/mt2),BP (mmHg),VWS (m/s)

COLUMN_MAP = {
    "Timestamp": "time",
    # Particulate matter
    "PM2.5 (µg/m³)": "pm25",
    "PM10 (µg/m³)": "pm10",
    # Nitrogen oxides
    "NO (µg/m³)": "no",
    "NO2 (µg/m³)": "no2",
    "NOx (ppb)": "nox",
    # Other gases
    "NH3 (µg/m³)": "nh3",
    "SO2 (µg/m³)": "so2",
    "CO (mg/m³)": "co",
    "Ozone (µg/m³)": "o3",
    # VOCs
    "Benzene (µg/m³)": "benzene",
    "Toluene (µg/m³)": "toluene",
    "Xylene (µg/m³)": "xylene",
    "O Xylene (µg/m³)": "o_xylene",
    "Eth-Benzene (µg/m³)": "ethyl_benzene",
    "MP-Xylene (µg/m³)": "mp_xylene",
    # Meteorology
    "AT (°C)": "average_temperature",
    "RH (%)": "relative_humidity",
    "WS (m/s)": "wind_speed",
    "WD (deg)": "wind_direction",
    "RF (mm)": "rainfall",
    "TOT-RF (mm)": "total_rainfall",
    "SR (W/mt2)": "solar_radiation",
    "BP (mmHg)": "pressure",
    "VWS (m/s)": "vertical_wind_speed",
}

# Load station metadata
stations_df = pd.read_csv(STATION_META_PATH)

# Normalize station names for join
stations_df["StationKey"] = stations_df["StationName"].str.lower().str.replace(" ", "")
print(stations_df.head())

all_dfs = []

pattern = re.compile(r"(site_\d+)_(.*?)_(CPCB|KSPCB)\.csv")
output = pattern.match("site_1556_Jayanagar_5th_Block_KSPCB.csv")
print(output.groups()) if output else print("No match")
# ('site_1556', 'Jayanagar_5th_Block', 'KSPCB')


def to_pascal_case(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("_"))


for file in tqdm(list(RAW_DIR.glob("*.csv"))):
    match = pattern.match(file.name)
    if not match:
        logger.warning(
            f"Filename {file.name} does not match expected pattern. Skipping."
        )
        continue

    station_id, station_name, org = match.groups()

    # normalize name
    station_key = to_pascal_case(station_name).lower()

    # load data
    df = pd.read_csv(file)

    # rename columns
    df = df.rename(columns=COLUMN_MAP)

    # keep only required columns
    df = df[[col for col in COLUMN_MAP.values() if col in df.columns]]
# convert CO from mg/m3 to µg/m3
    if "co" in df.columns:
        df["co"] = df["co"] * 1000
        
    # add metadata
    df["station_name"] = to_pascal_case(station_name)
    site_num = int(station_id.split("_")[1])
    df["site"] = site_num
    df["org"] = org

    # attach lat/lon
    meta_row = stations_df[stations_df["StationKey"] == station_key]

    if not meta_row.empty:
        df["latitude"] = meta_row.iloc[0]["Latitude"]
        df["longitude"] = meta_row.iloc[0]["Longitude"]
    else:
        df["latitude"] = None
        df["longitude"] = None

    # convert time
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    all_dfs.append(df)

# merge all
master_df = pd.concat(all_dfs, ignore_index=True)

# sort
master_df = master_df.sort_values(["time", "station_name"])

master_df.to_csv(DATASET_DIR / "artifacts" / "master_dataset.csv", index=False)
# drop bad rows
# master_df = master_df.dropna(subset=["time", "pm25", "wind_speed", "wind_direction"])

print(master_df.head())

