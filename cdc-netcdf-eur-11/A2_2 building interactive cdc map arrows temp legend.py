import xarray as xr
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import math  # Required for calculating arrow direction
from branca.element import MacroElement
from jinja2 import Template

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

    # Check for valid `swh` and `mwd` values before plotting
    if not pd.isna(swh) and not pd.isna(mwd):
        # Tooltip for displaying wave height and direction
        tooltip = (
            f"Wave Height (swh): {swh:.2f} m<br>"
            f"Wave Direction (mwd): {mwd:.2f}°"
        )

        # Add a circular marker for wave height
        folium.CircleMarker(
            location=(lat, lon),
            radius=swh * 2,  # Adjust radius based on wave height
            color="blue",
            fill=True,
            fill_opacity=0.6,
            tooltip=tooltip,
        ).add_to(marker_cluster)

        # Add an arrow for wave direction
        # Calculate the end point of the arrow using `mwd` (angle in degrees) and `lat`, `lon`
        arrow_length = 0.1  # Length of the arrow line in degrees
        dx = arrow_length * math.sin(math.radians(mwd))
        dy = arrow_length * math.cos(math.radians(mwd))

        # Draw a line representing the wave direction
        folium.PolyLine(
            locations=[(lat, lon), (lat + dy, lon + dx)],
            color="red",
            weight=2
        ).add_to(wave_map)

# Add a legend for wave height
legend_html = """
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 200px; height: 120px; 
    z-index:9999; font-size:14px;
    background-color:white; 
    border:2px solid grey; 
    border-radius:8px;
    padding: 10px;
    opacity: 0.9;">
    <b>Wave Height Legend</b><br>
    <i style="background:blue; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Small Waves (Low SWH)<br>
    <i style="background:blue; width:20px; height:20px; display:inline-block; border-radius:50%;"></i> Medium Waves<br>
    <i style="background:blue; width:30px; height:30px; display:inline-block; border-radius:50%;"></i> Large Waves (High SWH)<br>
</div>
"""

legend = MacroElement()
legend._template = Template(legend_html)
wave_map.get_root().add_child(legend)

# Save the map to an HTML file
wave_map.save("interactive_wave_map_with_arrows_and_legend.html")
print("Interactive wave map with arrows and legend saved as 'interactive_wave_map_with_arrows_and_legend.html'")
