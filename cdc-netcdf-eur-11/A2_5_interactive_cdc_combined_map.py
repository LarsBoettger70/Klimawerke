import xarray as xr
import numpy as np
import folium
from folium.plugins import TimeSliderChoropleth

# Load primary wave data file
wave_file = "data_stream-wave_stepType-instant.nc"
ds_wave = xr.open_dataset(wave_file)

# Load additional weather data files
weather_file = "data_stream-oper_stepType-instant.nc"
precip_file = "data_stream-oper_stepType-accum.nc"
ds_weather = xr.open_dataset(weather_file)
ds_precip = xr.open_dataset(precip_file)

# Extract wave variables
lat = ds_wave["latitude"].values
lon = ds_wave["longitude"].values
time = ds_wave["valid_time"].values
swh = ds_wave["swh"].values

# Extract weather-related variables
t2m = ds_weather["t2m"].values - 273.15  # Temperature in Celsius
tp = ds_precip["tp"].values if "tp" in ds_precip else np.zeros_like(t2m)  # Precipitation (fallback if missing)

# Calculate additional metrics
wind_speed = np.sqrt(ds_weather["u10"].values**2 + ds_weather["v10"].values**2)

# Initialize the folium map
wave_map = folium.Map(location=[float(lat.mean()), float(lon.mean())], zoom_start=6, tiles="OpenStreetMap")

# Initialize FeatureGroups for layering
wave_height_layer = folium.FeatureGroup(name="Wave Height", overlay=True)

# TimeSliderChoropleth setup and styles
time_slider_data = {}
styledict = {}

# Process data dynamically across time steps
for t_index, t_val in enumerate(time):
    timestamp = str(np.datetime_as_string(t_val, unit="h"))  # Convert time to string
    styledict[timestamp] = {}

    for i, lat_val in enumerate(lat):
        for j, lon_val in enumerate(lon):
            swh_val = float(swh[t_index, i, j]) if np.isfinite(swh[t_index, i, j]) else 0
            properties = {"time": timestamp, "wave_height": swh_val}
            circle_style = {
                "radius": swh_val * 5000,  # Convert radius to float
                "color": "blue",
                "fillColor": "blue",
                "fillOpacity": 0.4,
            }

            # Add point data to GeoJSON
            styledict[timestamp][f"{lat_val}-{lon_val}"] = circle_style

wave_height_layer.add_to(wave_map)

# Add dynamic TimeSliderChoropleth
time_slider = TimeSliderChoropleth(data=time_slider_data, styledict=styledict)
time_slider.add_to(wave_map)

# Save map to HTML
wave_map.save("interactive_wave_weather_map_dynamic.html")
print("Map saved successfully: interactive_wave_weather_map_dynamic.html")
