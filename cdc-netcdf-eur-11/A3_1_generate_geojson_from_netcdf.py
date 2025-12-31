'''
GeoJSON Generator from NetCDF files
Processes CDC European weather and wave data and generates GeoJSON files for visualization
'''

import xarray as xr
import numpy as np
import json
import os
from scipy.interpolate import griddata
from datetime import datetime
import sys

# File paths
WAVE_FILE = 'data_stream-wave_stepType-instant.nc'
WEATHER_INSTANT_FILE = 'data_stream-oper_stepType-instant.nc'
WEATHER_ACCUM_FILE = 'data_stream-oper_stepType-accum.nc'
OUTPUT_DIR = 'geojson'


def load_netcdf_files():
    '''Load all three NetCDF files'''
    print('Loading NetCDF files...')
    
    if not os.path.exists(WAVE_FILE):
        print(f'✗ Error: {WAVE_FILE} not found')
        return None, None, None
    if not os.path.exists(WEATHER_INSTANT_FILE):
        print(f'✗ Error: {WEATHER_INSTANT_FILE} not found')
        return None, None, None
    if not os.path.exists(WEATHER_ACCUM_FILE):
        print(f'✗ Error: {WEATHER_ACCUM_FILE} not found')
        return None, None, None
    
    try:
        ds_wave = xr.open_dataset(WAVE_FILE)
        ds_weather_inst = xr.open_dataset(WEATHER_INSTANT_FILE)
        ds_weather_accum = xr.open_dataset(WEATHER_ACCUM_FILE)
        
        print(f'✓ Loaded {WAVE_FILE}')
        print(f'  - Dimensions: {dict(ds_wave.dims)}')
        print(f'  - Variables: {list(ds_wave.data_vars)}')
        
        print(f'✓ Loaded {WEATHER_INSTANT_FILE}')
        print(f'  - Dimensions: {dict(ds_weather_inst.dims)}')
        print(f'  - Variables: {list(ds_weather_inst.data_vars)}')
        
        print(f'✓ Loaded {WEATHER_ACCUM_FILE}')
        print(f'  - Dimensions: {dict(ds_weather_accum.dims)}')
        print(f'  - Variables: {list(ds_weather_accum.data_vars)}')
        
        return ds_wave, ds_weather_inst, ds_weather_accum
    except Exception as e:
        print(f'✗ Error loading files: {e}')
        return None, None, None


def interpolate_wave_to_weather_grid(ds_wave, target_lat, target_lon):
    '''
    Interpolate wave data from 17x21 grid to 33x41 weather grid
    Uses scipy griddata for 2D interpolation
    '''
    print('\nInterpolating wave data to weather grid...')
    
    # Get wave grid coordinates
    wave_lat = ds_wave['latitude'].values
    wave_lon = ds_wave['longitude'].values
    
    # Create meshgrid for wave data (source)
    wave_lon_grid, wave_lat_grid = np.meshgrid(wave_lon, wave_lat)
    wave_points = np.column_stack([wave_lat_grid.flatten(), wave_lon_grid.flatten()])
    
    # Create meshgrid for weather data (target)
    target_lon_grid, target_lat_grid = np.meshgrid(target_lon, target_lat)
    target_points = np.column_stack([target_lat_grid.flatten(), target_lon_grid.flatten()])
    
    # Interpolate each wave variable for each time step
    n_times = len(ds_wave['valid_time'])
    n_target_lat = len(target_lat)
    n_target_lon = len(target_lon)
    
    interpolated_data = {}
    
    for var in ['swh', 'mwd', 'mwp']:
        print(f'  Interpolating {var}...')
        interpolated_data[var] = np.zeros((n_times, n_target_lat, n_target_lon))
        
        for t in range(n_times):
            if t % 100 == 0:
                print(f'    Time step {t}/{n_times}')
            
            # Get wave data for this time step
            wave_data = ds_wave[var].isel(valid_time=t).values
            wave_values = wave_data.flatten()
            
            # Remove NaN values for interpolation
            valid_mask = ~np.isnan(wave_values)
            if np.any(valid_mask):
                # Interpolate to target grid
                interpolated = griddata(
                    wave_points[valid_mask],
                    wave_values[valid_mask],
                    target_points,
                    method='linear',
                    fill_value=np.nan
                )
                interpolated_data[var][t] = interpolated.reshape(n_target_lat, n_target_lon)
            else:
                interpolated_data[var][t] = np.full((n_target_lat, n_target_lon), np.nan)
    
    print('✓ Wave data interpolation complete')
    return interpolated_data


def calculate_wind_speed(u10, v10):
    '''Calculate wind speed from U and V components'''
    return np.sqrt(u10**2 + v10**2)


def generate_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave):
    '''
    Generate GeoJSON files for each variable/time combination
    '''
    print('\nGenerating GeoJSON files...')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get coordinates (use weather grid as reference)
    lats = ds_weather_inst['latitude'].values
    lons = ds_weather_inst['longitude'].values
    times = ds_weather_inst['valid_time'].values
    
    # Time series index for TimeSlider
    timeseries_index = {
        'timestamps': [],
        'files': {
            'swh': [],
            't2m': [],
            'tp': [],
            'wind_speed': [],
            'sst': []
        }
    }
    
    # Process only a subset of time steps for efficiency (every 24th time step = 1 per day)
    # This reduces from 576 to 24 time steps
    time_step_interval = 24
    total_steps = len(times)
    
    print(f'Processing {total_steps // time_step_interval} time steps (every {time_step_interval}th step)...')
    
    for t_idx in range(0, total_steps, time_step_interval):
        timestamp = pd.Timestamp(times[t_idx]).isoformat()
        print(f'\nProcessing time step {t_idx}/{total_steps}: {timestamp}')
        
        timeseries_index['timestamps'].append(timestamp)
        
        # Generate GeoJSON for each variable
        variables = {
            'swh': interpolated_wave['swh'][t_idx],
            't2m': ds_weather_inst['t2m'].isel(valid_time=t_idx).values - 273.15,  # Convert to Celsius
            'tp': ds_weather_accum['tp'].isel(valid_time=t_idx).values * 1000,  # Convert to mm
            'sst': ds_weather_inst['sst'].isel(valid_time=t_idx).values - 273.15,  # Convert to Celsius
        }
        
        # Calculate wind speed
        u10 = ds_weather_inst['u10'].isel(valid_time=t_idx).values
        v10 = ds_weather_inst['v10'].isel(valid_time=t_idx).values
        variables['wind_speed'] = calculate_wind_speed(u10, v10)
        
        # Create GeoJSON for each variable
        for var_name, var_data in variables.items():
            features = []
            
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    value = float(var_data[i, j])
                    
                    # Skip NaN values
                    if np.isnan(value):
                        continue
                    
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [float(lon), float(lat)]
                        },
                        'properties': {
                            'value': round(value, 3),
                            'lat': float(lat),
                            'lon': float(lon),
                            'timestamp': timestamp
                        }
                    }
                    features.append(feature)
            
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            # Save GeoJSON file
            filename = f'{var_name}_{timestamp.replace(":", "-")}.geojson'
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'w') as f:
                json.dump(geojson, f)
            
            timeseries_index['files'][var_name].append(filename)
            
            print(f'  ✓ Created {filename} ({len(features)} features)')
    
    # Save timeseries index
    index_file = os.path.join(OUTPUT_DIR, 'timeseries_index.json')
    with open(index_file, 'w') as f:
        json.dump(timeseries_index, f, indent=2)
    
    print(f'\n✓ Timeseries index saved to {index_file}')
    print(f'✓ Generated {len(timeseries_index["timestamps"])} time steps')


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - GeoJSON Generator')
    print('=' * 70)
    
    # Load NetCDF files
    ds_wave, ds_weather_inst, ds_weather_accum = load_netcdf_files()
    if ds_wave is None:
        print('\n✗ Failed to load NetCDF files')
        return
    
    # Get target grid (weather grid)
    target_lat = ds_weather_inst['latitude'].values
    target_lon = ds_weather_inst['longitude'].values
    
    # Interpolate wave data
    interpolated_wave = interpolate_wave_to_weather_grid(ds_wave, target_lat, target_lon)
    
    # Generate GeoJSON files
    generate_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave)
    
    print('\n' + '=' * 70)
    print('✓ GeoJSON GENERATION COMPLETE!')
    print('=' * 70)
    print(f'\nGenerated files in: {OUTPUT_DIR}/')
    print('Next step: Run A3_2_build_interactive_map_with_timeslider.py')
    print('=' * 70)


if __name__ == '__main__':
    import pandas as pd  # Import here to avoid issues with timestamp conversion
    main()
