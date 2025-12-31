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

# Save wave_df to a CSV file for inspection
wave_df.to_csv("wave_data.csv", index=False)
print("Wave data saved to wave_data.csv")
