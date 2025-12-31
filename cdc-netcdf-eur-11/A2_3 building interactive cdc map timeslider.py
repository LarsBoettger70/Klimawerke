import xarray as xr
import numpy as np
import folium
from folium.plugins import TimeSliderChoropleth
import math
from branca.element import MacroElement
from jinja2 import Template

# Load Wave Data
wave_file = "data_stream-wave_stepType-instant.nc"
ds_wave = xr.open_dataset(wave_file)

# Extract relevant variables for wave data
lat = ds_wave["latitude"].values
lon = ds_wave["longitude"].values
time = ds_wave["valid_time"].values  # Time dimension
swh = ds_wave["swh"].values  # All time slices
mwd = ds_wave["mwd"].values  # All time slices

# Create a base folium map
wave_map = folium.Map(location=[float(lat.mean()), float(lon.mean())], zoom_start=6, tiles="OpenStreetMap")

# Layer Control Groups
legend_control = folium.map.LayerControl()

# Legend HTML for Wave Height, Weather Variables, and Other Layers
legend_html = """
<div style="
    position: fixed;
    bottom: 50px; left: 50px; width: 250px; height: 150px;
    z-index:9999; font-size:14px;
    background-color:white;
    border:1px solid grey;
    border-radius:8px;
    padding:10px;
    opacity:0.9;">
    <b>Layer Legend</b><br>
    <i style="background:blue; width:10px; height:10px; display:inline-block;"></i> Wave Height<br>
    <i style="background:red; width:10px; height:10px; display:inline-block;"></i> Wave Direction<br>
    <i style="background:green; width:10px; height:10px; display:inline-block;"></i> Temperature<br>
    <i style="background:purple; width:10px; height:10px; display:inline-block;"></i> Precipitation
</div>
"""
legend = MacroElement()
legend._template = Template(legend_html)
wave_map.get_root().add_child(legend)

# Generate time slider data and styledict for wave height
time_slider_data = {}
styledict = {}
for t_index, t in enumerate(time):
    timestamp = str(t_index)  # Use t_index as a key
    time_slider_data[timestamp] = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(lon[0]), float(lat[0])],  # Adjust lon/lat as needed
        },
        "properties": {"time": timestamp},
    }
    styledict[timestamp] = {
        "color": "blue",
        "opacity": 0.5,
        "weight": 2,
        "radius": 5 + (t_index % 3)  # Dynamically change radius for demo
    }

# Weather Data
weather_file = "data_stream-oper_stepType-instant.nc"
precip_file = "data_stream-oper_stepType-accum.nc"
ds_weather = xr.open_dataset(weather_file)
ds_precip = xr.open_dataset(precip_file)

t2m = ds_weather["t2m"].isel(valid_time=0).values - 273.15  # Temperature in Celsius
tp = ds_precip["tp"].isel(valid_time=0).values  # Total Precipitation

# Add layers for temperature and precipitation
temperature_layer = folium.FeatureGroup(name="Temperature (t2m)", overlay=True)
precip_layer = folium.FeatureGroup(name="Precipitation (tp)", overlay=True)

for i, lat_val in enumerate(lat):
    for j, lon_val in enumerate(lon):
        temp = float(t2m[i, j]) if not np.isnan(t2m[i, j]) else None
        prec = float(tp[i, j]) if not np.isnan(tp[i, j]) else None
        if temp:
            folium.CircleMarker(
                location=[float(lat_val), float(lon_val)],
                radius=4,
                color="green",
                fill=True,
                fill_opacity=0.4,
                tooltip=f"Temperature: {temp:.2f} °C"
            ).add_to(temperature_layer)
        if prec:
            folium.CircleMarker(
                location=[float(lat_val), float(lon_val)],
                radius=5,
                color="purple",
                fill=True,
                fill_opacity=0.4,
                tooltip=f"Precipitation: {prec:.2f} mm"
            ).add_to(precip_layer)

wave_map.add_child(temperature_layer)
wave_map.add_child(precip_layer)

# Add TimeSliderChoropleth for dynamic updates
time_slider = TimeSliderChoropleth(
    data=time_slider_data,
    styledict=styledict
)
time_slider.add_to(wave_map)

# Add layer control and finalize the map
folium.LayerControl().add_to(wave_map)

# Save the final map
wave_map.save("interactive_wave_weather_map_with_sliders_and_legend.html")
print("Map created: interactive_wave_weather_map_with_sliders_and_legend.html")
