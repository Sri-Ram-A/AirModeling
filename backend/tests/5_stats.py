import pandas as pd
from pathlib import Path
from pprint import pprint
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

ROOT_DIR = Path(__name__).resolve().parent
DATASET_DIR = ROOT_DIR / "backend" / "data"
ARTIFACTS_DIR = DATASET_DIR / "artifacts"

df = pd.read_csv(ARTIFACTS_DIR / "master_dataset.csv")


# { // groupby("station_name") function working
#     "BTMLayout": DataFrame,
#     "Peenya": DataFrame,
#     ...
# }
for name, group in df.groupby("station_name"):
    print(f"\n=== {name} ===")
    pprint(group.head())

df["time"] = pd.to_datetime(df["time"], errors="coerce")
print(df["time"].dtype)
# datetime64[us]
df["month"] = df["time"].dt.to_period("M").astype(str)

# { // df.groupby(["station_name", "month"])
#   ("Peenya", "2025-01"): df_subset,
#   ("Peenya", "2025-02"): df_subset,
#   ...
# }
## How to Access These Groups?
# for (station, month), group in df.groupby(["station_name", "month"]):
#     print(station, month)
#     print(group.head())

nan_counts = (
    df.groupby(["station_name", "month"])
    .apply(lambda g: g.isna().sum().sum())  # total NaNs in that group
    .reset_index(name="nan_count")
)
## Equivalent Explicit Version
# rows = []
# for (station, month), group in df.groupby(["station_name", "month"]):
#     nan_count = group.isna().sum().sum()
#     rows.append({
#         "station_name": station,
#         "month": month,
#         "nan_count": nan_count
#     })

# nan_counts = pd.DataFrame(rows)
g = sns.FacetGrid(nan_counts, col="station_name", col_wrap=3, sharey=False)
g.map_dataframe(sns.barplot, x="month", y="nan_count")
g.set_titles("{col_name}")
for ax in g.axes:
    ax.tick_params(axis="x", rotation=45)

plt.show()

fig = px.bar(
    nan_counts,
    x="month",
    y="nan_count",
    facet_col="station_name",
    facet_col_wrap=3,
    title="Analysis of Missing Data per Station",
    labels={"nan_count": "Missing Values", "month": "Month", "station_name": "Station"},
    template="plotly_white",  # Clean, professional look
    color="nan_count",  # Adds a color scale based on severity
    color_continuous_scale="Viridis",
)

# Refine the layout
fig.update_layout(
    title_font_size=24,
    margin=dict(t=80, l=40, r=40, b=40),  # Adds breathing room
    showlegend=False,
)
fig.write_html(ARTIFACTS_DIR / "missing_data_report.html")
fig.show()
