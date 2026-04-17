import pandas as pd
import folium
from pathlib import Path

ROOT_DIR = Path(__name__).resolve().parent
DATASET_DIR = ROOT_DIR / "backend" / "data"

df = pd.read_csv(DATASET_DIR / "raw" / "stations.csv")
print(df.head())
print(df.columns)
# Index(['SlNo', 'StationName', 'Organization', 'Latitude', 'Longitude'], dtype='str')

# Create a folium map centered around the average location of the stations
folium_map = folium.Map(
    location=[df.Latitude.mean(), df.Longitude.mean()], zoom_start=11
)
for _, row in df.iterrows():
    folium.Marker(
        [row.Latitude, row.Longitude],
        tooltip=folium.Tooltip(
            f"{row.StationName} ({row.Organization})",
            sticky=True,  # follows cursor slightly
        ),
        popup=row.StationName,
    ).add_to(folium_map)
folium_map.save(DATASET_DIR / "artifacts" / "stations_map.html")
