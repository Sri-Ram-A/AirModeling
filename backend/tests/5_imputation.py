# P | Method	                | When to Use	                            | Why
# 1	| Linear interpolation	    | Gaps < 6 hours (24 consecutive missing)	| Preserves trends between valid readings
# 2	| Same time previous day	| Gaps 6-48 hours	                        | Captures daily patterns (e.g., rush hour traffic)
# 3	| Same day previous week	| Gaps 2-7 days	                            | Captures weekly patterns (weekday vs weekend)
# 4	| Monthly median by hour	| Large gaps or seasonal patterns	        | Accounts for seasonal variation
# 5	| Station median	        | Everything else fails	                    | Last resort baseline

# Block 1 — Imports & Config
from pathlib import Path
import pandas as pd
import numpy as np
from pprint import pprint
from tqdm import tqdm
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Configuration
MAX_GAP_INTERPOLATION = 24  # 24 * 15min = 6 hours
MAX_GAP_PREVIOUS_DAY = 192  # 192 * 15min = 48 hours
MAX_GAP_PREVIOUS_WEEK = 672  # 672 * 15min = 7 days

CIRCULAR_COLUMNS = ["wind_direction"]
FORWARD_FILL_COLUMNS = ["rainfall", "total_rainfall"]

imputation_log = {}


# Block 2 — Paths & Load Data
ROOT_DIR = Path().cwd()
DATASET_DIR = ROOT_DIR / "backend" / "data"
ARTIFACTS_DIR = DATASET_DIR / "artifacts"
MASTER_PATH = ARTIFACTS_DIR / "master_dataset.csv"
IMPUTED_PATH = ARTIFACTS_DIR / "final_master_dataset.csv"

master_df = pd.read_csv(MASTER_PATH)
master_df["time"] = pd.to_datetime(master_df["time"])

print(
    f"Loaded {len(master_df)} records from {master_df['station_name'].nunique()} stations"
)
master_df.head()


# Block 3.1 — Inspect Missing Values
missing_summary = master_df.isnull().mean().sort_values(ascending=False).round(2) * 100
missing_cols = missing_summary[missing_summary > 0]
print("Missing value summary:")
print(missing_cols)

# o_xylene               100.0
# xylene                 100.0
# vertical_wind_speed     92.0
# rainfall                73.0
# ethyl_benzene           72.0
# solar_radiation         67.0
# mp_xylene               65.0
# total_rainfall          63.0
# wind_speed              48.0
# wind_direction          40.0
# pressure                40.0
# toluene                 38.0
# average_temperature     33.0
# nh3                     29.0
# pm25                    29.0
# benzene                 27.0
# o3                      26.0
# no                      23.0
# relative_humidity       22.0
# nox                     21.0
# co                      19.0
# pm10                    17.0
# so2                     16.0
# longitude               15.0
# latitude                15.0
# no2                     15.0

# Block 3.2 - Dropping [o_xylene,xylene,vertical_wind_speed]
master_df = master_df.drop(columns=["o_xylene", "xylene", "vertical_wind_speed"])
pprint(master_df.columns)

# Index(['time', 'pm25', 'pm10', 'no', 'no2', 'nox', 'nh3', 'so2', 'co', 'o3',
#        'benzene', 'toluene', 'ethyl_benzene', 'mp_xylene',
#        'average_temperature', 'relative_humidity', 'wind_speed',
#        'wind_direction', 'rainfall', 'total_rainfall', 'solar_radiation',
#        'pressure', 'station_name', 'site', 'org', 'latitude', 'longitude'],
#       dtype='str')


# Block 4 — Helper: Circular Interpolation (wind direction)
def circular_interpolate(series):
    """Handles 0-360° wrap-around correctly"""
    radians = np.radians(series)
    sin_interp = np.sin(radians).interpolate(method="linear", limit_direction="both")
    cos_interp = np.cos(radians).interpolate(method="linear", limit_direction="both")
    interpolated = np.degrees(np.arctan2(sin_interp, cos_interp)) % 360
    return pd.Series(interpolated, index=series.index)

# Just to see if dataset is already having proper 15 mins split 
master_df = master_df.sort_values(["station_name", "time"])
time_gaps = (
    master_df.groupby("station_name")["time"]
    .diff()
    .value_counts()
)
print(time_gaps.head(10))
# 0 days 00:15:00    467218

# Block 5 — Pick a Station to Work On
# Change this to whichever station you want
STATION_NAMES = master_df["station_name"].unique()
all_imputed_dfs = []
for STATION_NAME in tqdm(
    STATION_NAMES, total=len(STATION_NAMES), desc="Imputing station"
):
    print("Available stations:", master_df["station_name"].unique())

    df = master_df[master_df["station_name"] == STATION_NAME].copy()
    df["time"] = pd.to_datetime(df["time"])
    df = (
        df.set_index("time").sort_index().asfreq("15min")
    )  # Introduces new rows/timestamps based on 15 mins frequency
    print(f"\nWorking on: {STATION_NAME}")
    print(f"Shape: {df.shape}")
    df.head()

    # Block 6 — Step 1: Linear Interpolation (gaps < 6 hrs)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(f"Columns not included are : {list(set(df.columns) - set(numeric_cols))}")
    # ['org', 'station_name']

    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        if df[col].isna().sum() == 0:
            print(f"No null values - hence skkipping column - {col}")
            continue
        if col in FORWARD_FILL_COLUMNS:
            df[col] = df[col].ffill().fillna(0)
        elif col in CIRCULAR_COLUMNS:
            df[col] = circular_interpolate(df[col])
        else:
            df[col] = df[col].interpolate(method="linear", limit=MAX_GAP_INTERPOLATION)

    print("After linear interpolation:")
    print(df[numeric_cols].isna().mean()[df[numeric_cols].isna().sum() > 0] * 100)

    # Step 6.5 — Recent-window fallback (≤ 1 hour)
    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        if df[col].isna().sum() == 0:
            continue
        for idx in df[df[col].isna()].index:
            start = idx - pd.Timedelta(hours=1)
            window = df.loc[start:idx, col]
            if window.notna().sum() > 0:
                df.loc[idx, col] = window.median()  # or mean()
                imputation_log.setdefault(STATION_NAME, []).append(
                    {"time": idx, "col": col, "method": "past_1hr_window"}
                )
    print("After 1 hour interpolation:")
    print(df[numeric_cols].isna().mean()[df[numeric_cols].isna().sum() > 0] * 100)

    # Block 7 — Step 2: Same Time Previous Day (gaps 6–48 hrs)
    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        if df[col].isna().sum() == 0:
            continue
        for idx in df[df[col].isna()].index:
            prev = idx - pd.Timedelta(days=1)
            if prev in df.index and pd.notna(df.loc[prev, col]):
                df.loc[idx, col] = df.loc[prev, col]
                imputation_log.setdefault(STATION_NAME, []).append(
                    {"time": idx, "col": col, "method": "previous_day"}
                )

    print("After previous-day fill:")
    print(df[numeric_cols].isna().sum()[df[numeric_cols].isna().sum() > 0])

    # df["latitude"].index - returns indices (in this case time column is index because of line 102)

    # Block 8 — Step 3: Same Time Previous Week (gaps 2–7 days)
    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        if df[col].isna().sum() == 0:
            continue
        for idx in df[df[col].isna()].index:
            prev = idx - pd.Timedelta(days=7)
            if prev in df.index and pd.notna(df.loc[prev, col]):
                df.loc[idx, col] = df.loc[prev, col]
                imputation_log.setdefault(STATION_NAME, []).append(
                    {"time": idx, "col": col, "method": "previous_week"}
                )

    print("After previous-week fill:")
    print(df[numeric_cols].isna().sum()[df[numeric_cols].isna().sum() > 0])

    # Block 9 — Step 4: Monthly Hour Median
    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        if df[col].isna().sum() == 0:
            continue
        medians = df.groupby([df.index.month, df.index.hour])[col].median()
        for idx in df[df[col].isna()].index:
            key = (idx.month, idx.hour)
            if key in medians.index and pd.notna(medians[key]):
                df.loc[idx, col] = medians[key]
                imputation_log.setdefault(STATION_NAME, []).append(
                    {"time": idx, "col": col, "method": "monthly_hour_median"}
                )

    print("After monthly-hour-median fill:")
    print(df[numeric_cols].isna().sum()[df[numeric_cols].isna().sum() > 0])

    # Block 10 — Step 5: Column Median Fallback
    for col in tqdm(numeric_cols, total=len(numeric_cols), desc="Imputing"):
        n = df[col].isna().sum()
        if n > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            print(f"  {col}: filled {n} remaining with median={median_val:.2f}")
            imputation_log.setdefault(STATION_NAME, []).append(
                {"col": col, "method": "column_median", "n_filled": n}
            )

    print("\nAll missing after fallback:")
    print(df[numeric_cols].isna().sum()[df[numeric_cols].isna().sum() > 0])
    print(
        "Done!" if df[numeric_cols].isna().sum().sum() == 0 else "Still some missing!"
    )
    df_out = df.reset_index()
    all_imputed_dfs.append(df_out)


# Block 11 — Review & Save
# Review imputation log
log_df = pd.DataFrame(
    [
        {"station": station, **entry}
        for station, entries in imputation_log.items()
        for entry in entries
    ]
)
print(log_df.sample(5))

# Precompute everything once
mc = log_df["method"].value_counts()
cc = log_df["col"].value_counts().head(15)
daily = log_df.dropna(subset=["time"]).set_index("time").resample("D").size()
pivot = pd.crosstab(log_df["col"], log_df["method"])

# For stacked bar
melted = pivot.reset_index().melt(id_vars="col", var_name="method", value_name="count")

# Top stations
station_counts = (
    log_df.groupby("station").size().reset_index(name="count").nlargest(10, "count")
)

# Create 3x2 grid
fig = make_subplots(
    rows=3,
    cols=2,
    subplot_titles=[
        "Method Usage",
        "Top Columns",
        "Imputations Over Time",
        "Heatmap (Col x Method)",
        "Stacked Methods per Column",
        "Top Stations",
    ],
)

# 1. Method usage
fig.add_trace(go.Bar(x=mc.index, y=mc.values), row=1, col=1)

# 2. Top columns
fig.add_trace(go.Bar(x=cc.index, y=cc.values), row=1, col=2)

# 3. Time series
fig.add_trace(
    go.Scatter(x=daily.index, y=daily.values, mode="lines"),
    row=2,
    col=1,
)

# 4. Heatmap
fig.add_trace(
    go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="Viridis",
        showscale=False,
    ),
    row=2,
    col=2,
)

# 5. Stacked bar (methods per column)
for method in pivot.columns:
    fig.add_trace(
        go.Bar(
            x=pivot.index,
            y=pivot[method],
            name=method,
            showlegend=True,
        ),
        row=3,
        col=1,
    )

# Make it stacked
fig.update_layout(barmode="stack")

# 6. Top stations
fig.add_trace(
    go.Bar(x=station_counts["station"], y=station_counts["count"]),
    row=3,
    col=2,
)

# Final layout
fig.update_layout(
    height=1200,
    title_text="Imputation Dashboard (Unified)",
)

# Save
html_path = ARTIFACTS_DIR / "imputation_dashboard.html"
fig.write_html(str(html_path), include_plotlyjs="cdn")
fig.show()

# Reset index and save
final_df = pd.concat(all_imputed_dfs, ignore_index=True)
print((master_df.isna().mean() - final_df.isna().mean()).mean() * 100)
# time                   0.000000
# pm25                   0.136973
# pm10                   0.167429
# no                     0.156513
# no2                    0.149579
# nox                    0.136206
# nh3                    0.143241
# so2                    0.160849
# co                     0.185567
# o3                     0.106086
# benzene                0.117974
# toluene                0.082670
# ethyl_benzene          0.045155
# mp_xylene              0.049960
# average_temperature    0.105402
# relative_humidity      0.141636
# wind_speed             0.109271
# wind_direction         0.177248
# rainfall               0.729124
# total_rainfall         0.625026
# solar_radiation        0.066049
# pressure               0.099368
# station_name           0.000000
# site                   0.000000
# org                    0.000000
# latitude               0.000000
# longitude              0.000000
# dtype: float64
# 13.671580713649753

print("Null values in new dataset")
print((final_df.isna().mean()) * 100)
# time                    0.000000
# pm25                   14.998973
# pm10                    0.000000
# no                      7.499486
# no2                     0.000000
# nox                     7.499486
# nh3                    14.998973
# so2                     0.000000
# co                      0.000000
# o3                     14.998973
# benzene                14.998973
# toluene                29.997945
# ethyl_benzene          67.495377
# mp_xylene              59.995891
# average_temperature    22.498459
# relative_humidity       7.499486
# wind_speed             37.497432
# wind_direction         22.498459
# rainfall                0.000000
# total_rainfall          0.000000
# solar_radiation        59.995891
# pressure               29.997945
# station_name            0.000000
# site                    0.000000
# org                     0.000000
# latitude               14.998973
# longitude              14.998973
# usless ones : ['solar_radiation' , 'ethyl_benzene'. 'mp_xylene']

final_df.to_csv(IMPUTED_PATH, index=False)

print("Original:", len(master_df))
print("Imputed :", len(final_df))
print(f"Saved FULL dataset to {IMPUTED_PATH}")


