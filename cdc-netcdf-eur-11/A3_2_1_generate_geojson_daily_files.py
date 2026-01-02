'''
GeoJSON Generator from NetCDF files - Daily Files Version
Processes CDC European weather and wave data and generates one GeoJSON file per variable per day
Each daily file contains all 24 hours for that day
'''

import xarray as xr
import numpy as np
import json
import os
from scipy.interpolate import griddata
from datetime import datetime
import pandas as pd

# File paths
WAVE_FILE = 'data_stream-wave_stepType-instant.nc'
WEATHER_INSTANT_FILE = 'data_stream-oper_stepType-instant.nc'
WEATHER_ACCUM_FILE = 'data_stream-oper_stepType-accum.nc'
OUTPUT_DIR = 'geojson_daily'


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
        print(f'  - Time range: {ds_wave.valid_time.values[0]} to {ds_wave.valid_time.values[-1]}')
        
        print(f'✓ Loaded {WEATHER_INSTANT_FILE}')
        print(f'  - Dimensions: {dict(ds_weather_inst.dims)}')
        print(f'  - Variables: {list(ds_weather_inst.data_vars)}')
        
        print(f'✓ Loaded {WEATHER_ACCUM_FILE}')
        print(f'  - Dimensions:  {dict(ds_weather_accum.dims)}')
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
        print(f'  Interpolating {var}.. .')
        interpolated_data[var] = np.zeros((n_times, n_target_lat, n_target_lon))
        
        for t in range(n_times):
            if t % 50 == 0:
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


def generate_daily_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave):
    '''
    Generate one GeoJSON file per variable per DAY
    Each file contains all 24 hours for that day
    '''
    print('\nGenerating daily GeoJSON files...')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get coordinates (use weather grid as reference)
    lats = ds_weather_inst['latitude'].values
    lons = ds_weather_inst['longitude'].values
    times = ds_weather_inst['valid_time'].values
    
    # Group time steps by date
    dates_to_times = {}
    for t_idx, time in enumerate(times):
        date = pd.Timestamp(time).strftime('%Y-%m-%d')
        if date not in dates_to_times:
            dates_to_times[date] = []
        dates_to_times[date].append(t_idx)
    
    print(f'Processing {len(dates_to_times)} days with {len(times)} total hours...')
    print(f'Days: {min(dates_to_times.keys())} to {max(dates_to_times.keys())}')
    
    # Metadata
    metadata = {
        'version': '1.1',
        'type': 'daily_files',
        'description': 'One GeoJSON file per variable per day, containing all hourly data',
        'dates': sorted(dates_to_times.keys()),
        'grid':  {
            'lat_min': float(lats.min()),
            'lat_max': float(lats.max()),
            'lon_min': float(lons.min()),
            'lon_max': float(lons.max()),
            'lat_count': len(lats),
            'lon_count': len(lons)
        },
        'variables': {}
    }
    
    # Variable configurations
    var_configs = {
        'swh': {
            'name': 'Significant Wave Height',
            'unit': 'm',
            'color_scale': {
                'vmin': 0,
                'vmax': 4,
                'colors': ['#3288bd', '#66c2a5', '#abdda4', '#e6f598', '#fee08b', '#fdae61', '#f46d43', '#d53e4f']
            }
        },
        't2m': {
            'name': 'Temperature 2m',
            'unit':  '°C',
            'color_scale': {
                'vmin': -5,
                'vmax': 25,
                'colors': ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027']
            }
        },
        'tp': {
            'name': 'Total Precipitation',
            'unit': 'mm',
            'color_scale': {
                'vmin':  0,
                'vmax': 0.5,
                'colors':  ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b']
            }
        },
        'sst': {
            'name':  'Sea Surface Temperature',
            'unit': '°C',
            'color_scale': {
                'vmin': 5,
                'vmax': 20,
                'colors': ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027']
            }
        },
        'wind_speed': {
            'name': 'Wind Speed',
            'unit': 'm/s',
            'color_scale': {
                'vmin': 0,
                'vmax': 20,
                'colors': ['#ffffe5', '#fff7bc', '#fee391', '#fec44f', '#fe9929', '#ec7014', '#cc4c02', '#993404', '#662506']
            }
        }
    }
    
    # Process each variable
    for var_name, var_config in var_configs.items():
        print(f'\n{"="*70}')
        print(f'Processing variable: {var_name} - {var_config["name"]}')
        print(f'{"="*70}')
        
        metadata['variables'][var_name] = {
            'name': var_config['name'],
            'unit':  var_config['unit'],
            'color_scale': var_config['color_scale'],
            'files': []
        }
        
        # Process each day
        for date in sorted(dates_to_times.keys()):
            time_indices = dates_to_times[date]
            print(f'\n  Date: {date} ({len(time_indices)} hours)')
            
            features = []
            timestamps = []
            
            # Process each hour in this day
            for t_idx in time_indices:
                timestamp = pd.Timestamp(times[t_idx]).isoformat()
                hour = pd.Timestamp(times[t_idx]).hour
                timestamps.append(timestamp)
                
                # Get data for this variable/time
                if var_name == 'swh':
                    data = interpolated_wave['swh'][t_idx]
                elif var_name == 't2m':
                    data = ds_weather_inst['t2m'].isel(valid_time=t_idx).values - 273.15
                elif var_name == 'tp':
                    data = ds_weather_accum['tp'].isel(valid_time=t_idx).values * 1000
                elif var_name == 'sst':
                    data = ds_weather_inst['sst'].isel(valid_time=t_idx).values - 273.15
                elif var_name == 'wind_speed':
                    u10 = ds_weather_inst['u10'].isel(valid_time=t_idx).values
                    v10 = ds_weather_inst['v10'].isel(valid_time=t_idx).values
                    data = calculate_wind_speed(u10, v10)
                
                # Create features for this hour
                for i, lat in enumerate(lats):
                    for j, lon in enumerate(lons):
                        value = float(data[i, j])
                        
                        if np.isnan(value):
                            continue
                        
                        feature = {
                            'type':  'Feature',
                            'geometry': {
                                'type': 'Point',
                                'coordinates': [float(lon), float(lat)]
                            },
                            'properties': {
                                'value': round(value, 3),
                                'time': timestamp,
                                'date': date,
                                'hour': hour
                            }
                        }
                        features.append(feature)
            
            # Save daily file
            geojson = {
                'type': 'FeatureCollection',
                'metadata': {
                    'variable': var_name,
                    'name': var_config['name'],
                    'unit': var_config['unit'],
                    'date': date,
                    'hours': len(time_indices),
                    'timestamps': timestamps,
                    'color_scale': var_config['color_scale']
                },
                'features': features
            }
            
            filename = f'{var_name}_{date}.geojson'
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'w') as f:
                json.dump(geojson, f)
            
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f'    ✓ {filename}')
            print(f'      - {len(features)} features')
            print(f'      - {file_size_mb:.2f} MB')
            print(f'      - Hours: {len(timestamps)}')
            
            metadata['variables'][var_name]['files'].append({
                'filename': filename,
                'date': date,
                'hours': len(time_indices),
                'feature_count': len(features),
                'size_mb': round(file_size_mb, 2)
            })
    
    # Save metadata
    metadata_file = os.path.join(OUTPUT_DIR, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Calculate totals
    total_files = sum(len(v['files']) for v in metadata['variables'].values())
    total_size_mb = sum(
        f['size_mb']
        for v in metadata['variables'].values()
        for f in v['files']
    )
    
    print(f'\n{"="*70}')
    print('✓ GENERATION COMPLETE')
    print(f'{"="*70}')
    print(f'Metadata saved to: {metadata_file}')
    print(f'\nStatistics:')
    print(f'  - Total days: {len(dates_to_times)}')
    print(f'  - Total hours: {len(times)}')
    print(f'  - Total files: {total_files}')
    print(f'  - Total size:  {total_size_mb:.2f} MB')
    print(f'  - Avg file size: {total_size_mb/total_files:.2f} MB')
    print(f'\nOutput directory: {OUTPUT_DIR}/')


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - GeoJSON Generator')
    print('Version 1.1: Daily Files with Hourly Data')
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
    
    # Generate daily GeoJSON files
    generate_daily_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave)
    
    print('\n' + '=' * 70)
    print('Next step: Run A3_2_1_build_interactive_map_daily_files.py')
    print('=' * 70)


if __name__ == '__main__':
    main()
