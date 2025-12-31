import xarray as xr
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point
import geopandas as gpd

# Load the NetCDF file (Wave Data)
wave_file = "data_stream-wave_stepType-instant.nc"  # Replace with your file path
ds_wave = xr.open_dataset(wave_file)

# Extract relevant variables
lat = ds_wave["latitude"].values
lon = ds_wave["longitude"].values
swh = ds_wave["swh"].isel(valid_time=0).values  # First time slice
mwd = ds_wave["mwd"].isel(valid_time=0).values

# Create a DataFrame for easier handling
wave_data = []
for i in range(len(lat)):
    for j in range(len(lon)):
        wave_data.append({
            "latitude": lat[i],
            "longitude": lon[j],
            "swh": swh[i][j],
            "mwd": mwd[i][j],
        })

wave_df = pd.DataFrame(wave_data)

# Drop NaN rows, if any (incomplete grid points)
wave_df = wave_df.dropna()

# Create a base Folium map centered on the dataset’s latitude/longitude range
'''
wave_map = folium.Map(location=[wave_df["latitude"].mean(), wave_df["longitude"].mean()],
                      zoom_start=6, tiles="Stamen Terrain")
'''
                      
# Create a base Folium map with proper attribution
'''
wave_map = folium.Map(
    location=[wave_df["latitude"].mean(), wave_df["longitude"].mean()],
    zoom_start=6,
    tiles="Stamen Terrain",
    attr="Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL."
)
'''

# Use OpenStreetMap tiles (no custom attribution required)

wave_map = folium.Map(
    location=[wave_df["latitude"].mean(), wave_df["longitude"].mean()],
    zoom_start=6,
    tiles="OpenStreetMap"
)


# Add a marker cluster for wave height and direction visualization
marker_cluster = MarkerCluster().add_to(wave_map)

for _, row in wave_df.iterrows():
    lat = row["latitude"]
    lon = row["longitude"]
    swh = row["swh"]
    mwd = row["mwd"]

    if not pd.isna(swh) and not pd.isna(mwd):
        # Tooltip for displaying wave height and direction
        tooltip = (
            f"Wave Height (swh): {swh:.2f} m<br>"
            f"Wave Direction (mwd): {mwd:.2f}°"
        )

        # Add a marker to the map
        folium.CircleMarker(
            location=(lat, lon),
            radius=swh * 2,  # Adjust radius based on wave height
            color="blue",
            fill=True,
            fill_opacity=0.6,
            tooltip=tooltip,
        ).add_to(marker_cluster)

# Save map to an HTML file and display
wave_map.save("interactive_wave_map.html")
print("Interactive wave map saved as 'interactive_wave_map.html'")
