import xarray as xr
import numpy as np
import folium
from folium.plugins import TimeSliderChoropleth
from branca.element import Template, MacroElement

# Load the main wave data
wave_file = "data_stream-wave_stepType-instant.nc"
ds_wave = xr.open_dataset(wave_file)

# Extract wave variables
lat = ds_wave["latitude"].values
lon = ds_wave["longitude"].values
time = ds_wave["valid_time"].values
swh = ds_wave["swh"].values
mwd = ds_wave["mwd"].values

# Load additional weather data
weather_file = "data_stream-oper_stepType-instant.nc"
precip_file = "data_stream-oper_stepType-accum.nc"
ds_weather = xr.open_dataset(weather_file)
ds_precip = xr.open_dataset(precip_file)

# Extract new weather variables
t2m = ds_weather["t2m"].values - 273.15  # Temperature in Celsius
tp = ds_precip["tp"].values  # Precipitation (accumulated)
u10 = ds_weather["u10"].values  # Zonal wind
v10 = ds_weather["v10"].values  # Meridional wind
sst = ds_weather["sst"].values - 273.15 if "sst" in ds_weather else None

# Compute wind speed
wind_speed = np.sqrt(u10**2 + v10**2)  # Magnitude of wind vector

# Initialize the base map
wave_map = folium.Map(location=[float(lat.mean()), float(lon.mean())], zoom_start=6, tiles='OpenStreetMap')

# Add layers for wave height, direction, temperature, precipitation, etc.
wave_height_layer = folium.FeatureGroup(name="Wave Height", overlay=True)
temperature_layer = folium.FeatureGroup(name="Temperature (t2m)", overlay=True)
precip_layer = folium.FeatureGroup(name="Precipitation (tp)", overlay=True)
wind_layer = folium.FeatureGroup(name="Wind Speed", overlay=True)
sst_layer = folium.FeatureGroup(name="Sea Surface Temp (SST)", overlay=True)

# Add data dynamically for multiple time steps
for t_index in range(swh.shape[0]):
    for i, lat_val in enumerate(lat):
        for j, lon_val in enumerate(lon):
            # Handle NaN values gracefully
            swh_val = float(swh[t_index, i, j]) if not np.isnan(swh[t_index, i, j]) else None
            temp_val = float(t2m[t_index, i, j]) if not np.isnan(t2m[t_index, i, j]) else None
            prec_val = float(tp[t_index, i, j]) if not np.isnan(tp[t_index, i, j]) else None
            wind_val = float(wind_speed[t_index, i, j]) if not np.isnan(wind_speed[t_index, i, j]) else None
            sst_val = float(sst[t_index, i, j]) if sst is not None and not np.isnan(sst[t_index, i, j]) else None

            # Tooltip information
            tooltip = f"Time: {time[t_index]}<br>"

            # Add wave height circles
            if swh_val:
                folium.Circle(
                    location=[float(lat_val), float(lon_val)],
                    radius=swh_val * 5000,  # Scale appropriately
                    color="blue",
                    fill=True,
                    fill_opacity=0.6,
                    tooltip=tooltip + f"Wave Height (swh): {swh_val:.2f} m"
                ).add_to(wave_height_layer)

            # Add temperature markers
            if temp_val:
                folium.CircleMarker(
                    location=[float(lat_val), float(lon_val)],
                    radius=4,
                    color="green",
                    fill=True,
                    fill_opacity=0.4,
                    tooltip=tooltip + f"Temperature (t2m): {temp_val:.2f} °C"
                ).add_to(temperature_layer)

            # Add precipitation markers
            if prec_val:
                folium.CircleMarker(
                    location=[float(lat_val), float(lon_val)],
                    radius=5,
                    color="purple",
                    fill=True,
                    fill_opacity=0.4,
                    tooltip=tooltip + f"Precipitation (tp): {prec_val:.2f} mm"
                ).add_to(precip_layer)

            # Add wind speed markers
            if wind_val:
                folium.CircleMarker(
                    location=[float(lat_val), float(lon_val)],
                    radius=6,
                    color="cyan",
                    fill=True,
                    fill_opacity=0.4,
                    tooltip=tooltip + f"Wind Speed: {wind_val:.2f} m/s"
                ).add_to(wind_layer)

            # Add sea surface temperature (SST) markers
            if sst_val:
                folium.CircleMarker(
                    location=[float(lat_val), float(lon_val)],
                    radius=6,
                    color="orange",
                    fill=True,
                    fill_opacity=0.4,
                    tooltip=tooltip + f"Sea Surface Temp (SST): {sst_val:.2f} °C"
                ).add_to(sst_layer)

# Add all layers to the map
wave_map.add_child(wave_height_layer)
wave_map.add_child(temperature_layer)
wave_map.add_child(precip_layer)
wave_map.add_child(wind_layer)
wave_map.add_child(sst_layer)

# Add dynamic layer controls
folium.LayerControl().add_to(wave_map)

# Add a legend or script name in the bottom left corner of the map
script_label_html = """
<div style="
    position: fixed;
    bottom: 10px; left: 10px; width: 250px; height: 30px;
    z-index:9999; font-size:10px;
    background-color:white;
    border:1px solid grey;
    border-radius:8px;
    padding:5px;
    opacity:0.9;">
    Built by: A2_4 building interactive cdc map time layer 3 nc.py
</div>
"""
label = MacroElement()
label._template = Template(script_label_html)
wave_map.get_root().add_child(label)

# Save the final map
wave_map.save("interactive_wave_weather_map_integrated.html")
print("Map saved: interactive_wave_weather_map_integrated.html")
