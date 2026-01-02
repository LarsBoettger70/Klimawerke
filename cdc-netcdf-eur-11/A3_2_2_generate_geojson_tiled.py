'''
GeoJSON Generator from NetCDF files - Tiled Version
Processes CDC European weather and wave data and generates tiled GeoJSON files
Splits the geographic grid into tiles for efficient loading of visible regions
'''

import xarray as xr
import numpy as np
import json
import os
from scipy.interpolate import griddata
from datetime import datetime
import pandas as pd

# File paths
WAVE_FILE = 'data_stream-wave_stepType-instant. nc'
WEATHER_INSTANT_FILE = 'data_stream-oper_stepType-instant.nc'
WEATHER_ACCUM_FILE = 'data_stream-oper_stepType-accum.nc'
OUTPUT_DIR = 'geojson_tiled'

# Tiling configuration
TILE_ROWS = 4  # Split latitude into 4 rows
TILE_COLS = 4  # Split longitude into 4 columns
# Total tiles = 4 × 4 = 16 tiles


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
        print(f'  - Time range: {ds_wave.valid_time.values[0]} to {ds_wave. valid_time.values[-1]}')
        
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
    wave_lat = ds_wave['latitude']. values
    wave_lon = ds_wave['longitude'].values
    
    # Create meshgrid for wave data (source)
    wave_lon_grid, wave_lat_grid = np.meshgrid(wave_lon, wave_lat)
    wave_points = np.column_stack([wave_lat_grid. flatten(), wave_lon_grid.flatten()])
    
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
                interpolated_data[var][t] = interpolated. reshape(n_target_lat, n_target_lon)
            else:
                interpolated_data[var][t] = np. full((n_target_lat, n_target_lon), np.nan)
    
    print('✓ Wave data interpolation complete')
    return interpolated_data


def calculate_wind_speed(u10, v10):
    '''Calculate wind speed from U and V components'''
    return np.sqrt(u10**2 + v10**2)


def calculate_tile_bounds(lats, lons, tile_row, tile_col, tile_rows, tile_cols):
    '''
    Calculate latitude and longitude bounds for a specific tile
    
    Returns: 
        (lat_start, lat_end, lon_start, lon_end, lat_indices, lon_indices)
    '''
    n_lat = len(lats)
    n_lon = len(lons)
    
    # Calculate number of points per tile
    lat_per_tile = n_lat // tile_rows
    lon_per_tile = n_lon // tile_cols
    
    # Calculate start/end indices
    lat_start_idx = tile_row * lat_per_tile
    lat_end_idx = (tile_row + 1) * lat_per_tile if tile_row < tile_rows - 1 else n_lat
    
    lon_start_idx = tile_col * lon_per_tile
    lon_end_idx = (tile_col + 1) * lon_per_tile if tile_col < tile_cols - 1 else n_lon
    
    # Get actual lat/lon values
    tile_lats = lats[lat_start_idx:lat_end_idx]
    tile_lons = lons[lon_start_idx:lon_end_idx]
    
    return {
        'lat_min': float(tile_lats.min()),
        'lat_max': float(tile_lats.max()),
        'lon_min': float(tile_lons.min()),
        'lon_max': float(tile_lons.max()),
        'lat_indices': (lat_start_idx, lat_end_idx),
        'lon_indices': (lon_start_idx, lon_end_idx),
        'lats': tile_lats,
        'lons': tile_lons
    }


def generate_tiled_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave):
    '''
    Generate tiled GeoJSON files
    Structure:  {variable}_{date}_{hour: 02d}_tile-{row}-{col}.geojson
    '''
    print(f'\nGenerating tiled GeoJSON files ({TILE_ROWS}×{TILE_COLS} = {TILE_ROWS*TILE_COLS} tiles)...')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get coordinates (use weather grid as reference)
    lats = ds_weather_inst['latitude'].values
    lons = ds_weather_inst['longitude'].values
    times = ds_weather_inst['valid_time'].values
    
    print(f'Grid:  {len(lats)} latitudes × {len(lons)} longitudes')
    print(f'Points per tile: ~{(len(lats)//TILE_ROWS) * (len(lons)//TILE_COLS)}')
    
    # Calculate tile bounds
    tile_bounds = {}
    for row in range(TILE_ROWS):
        for col in range(TILE_COLS):
            tile_id = f'{row}-{col}'
            tile_bounds[tile_id] = calculate_tile_bounds(lats, lons, row, col, TILE_ROWS, TILE_COLS)
            bounds = tile_bounds[tile_id]
            print(f'  Tile {tile_id}:  Lat [{bounds["lat_min"]:.2f}, {bounds["lat_max"]:. 2f}], '
                  f'Lon [{bounds["lon_min"]:.2f}, {bounds["lon_max"]:.2f}]')
    
    # Group time steps by date
    dates_to_times = {}
    for t_idx, time in enumerate(times):
        date = pd.Timestamp(time).strftime('%Y-%m-%d')
        hour = pd.Timestamp(time).hour
        if date not in dates_to_times:
            dates_to_times[date] = {}
        dates_to_times[date][hour] = t_idx
    
    print(f'\nProcessing {len(dates_to_times)} days with {len(times)} total hours...')
    
    # Metadata
    metadata = {
        'version': '1.2',
        'type': 'tiled',
        'description': 'Tiled GeoJSON files for efficient loading of visible regions',
        'tiling': {
            'rows': TILE_ROWS,
            'cols': TILE_COLS,
            'total_tiles': TILE_ROWS * TILE_COLS,
            'tiles':  tile_bounds
        },
        'dates': sorted(dates_to_times.keys()),
        'grid': {
            'lat_min': float(lats.min()),
            'lat_max': float(lats.max()),
            'lon_min': float(lons. min()),
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
            'name':  'Temperature 2m',
            'unit': '°C',
            'color_scale': {
                'vmin': -5,
                'vmax': 25,
                'colors': ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027']
            }
        },
        'tp': {
            'name': 'Total Precipitation',
            'unit':  'mm',
            'color_scale': {
                'vmin': 0,
                'vmax': 0.5,
                'colors':  ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b']
            }
        },
        'sst': {
            'name': 'Sea Surface Temperature',
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
    
    # Statistics tracking
    total_files = 0
    total_size_mb = 0
    
    # Process each variable
    for var_name, var_config in var_configs.items():
        print(f'\n{"="*70}')
        print(f'Processing variable: {var_name} - {var_config["name"]}')
        print(f'{"="*70}')
        
        metadata['variables'][var_name] = {
            'name': var_config['name'],
            'unit':  var_config['unit'],
            'color_scale': var_config['color_scale'],
            'file_count': 0,
            'total_size_mb': 0
        }
        
        # Process each date
        for date in sorted(dates_to_times. keys()):
            print(f'\n  Date: {date}')
            
            # Process each hour
            for hour, t_idx in sorted(dates_to_times[date].items()):
                timestamp = pd.Timestamp(times[t_idx]).isoformat()
                
                # Get data for this variable/time
                if var_name == 'swh':
                    data = interpolated_wave['swh'][t_idx]
                elif var_name == 't2m':
                    data = ds_weather_inst['t2m']. isel(valid_time=t_idx).values - 273.15
                elif var_name == 'tp':
                    data = ds_weather_accum['tp'].isel(valid_time=t_idx).values * 1000
                elif var_name == 'sst':
                    data = ds_weather_inst['sst'].isel(valid_time=t_idx).values - 273.15
                elif var_name == 'wind_speed':
                    u10 = ds_weather_inst['u10'].isel(valid_time=t_idx).values
                    v10 = ds_weather_inst['v10'].isel(valid_time=t_idx).values
                    data = calculate_wind_speed(u10, v10)
                
                # Process each tile
                for tile_id, bounds in tile_bounds.items():
                    lat_start, lat_end = bounds['lat_indices']
                    lon_start, lon_end = bounds['lon_indices']
                    tile_lats = bounds['lats']
                    tile_lons = bounds['lons']
                    
                    # Extract data for this tile
                    tile_data = data[lat_start:lat_end, lon_start:lon_end]
                    
                    # Create features for this tile
                    features = []
                    for i, lat in enumerate(tile_lats):
                        for j, lon in enumerate(tile_lons):
                            value = float(tile_data[i, j])
                            
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
                            features. append(feature)
                    
                    # Skip empty tiles
                    if len(features) == 0:
                        continue
                    
                    # Save tiled file
                    geojson = {
                        'type': 'FeatureCollection',
                        'metadata': {
                            'variable': var_name,
                            'name': var_config['name'],
                            'unit': var_config['unit'],
                            'date': date,
                            'hour': hour,
                            'timestamp': timestamp,
                            'tile':  tile_id,
                            'bounds': {
                                'lat_min': bounds['lat_min'],
                                'lat_max': bounds['lat_max'],
                                'lon_min': bounds['lon_min'],
                                'lon_max': bounds['lon_max']
                            },
                            'color_scale': var_config['color_scale']
                        },
                        'features': features
                    }
                    
                    filename = f'{var_name}_{date}_{hour:02d}_tile-{tile_id}.geojson'
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    with open(filepath, 'w') as f:
                        json. dump(geojson, f)
                    
                    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    total_files += 1
                    total_size_mb += file_size_mb
                    metadata['variables'][var_name]['file_count'] += 1
                    metadata['variables'][var_name]['total_size_mb'] += file_size_mb
                
                if hour == 0 or hour == 12:   # Log progress at midnight and noon
                    print(f'    Hour {hour: 02d}:00 - Generated {TILE_ROWS*TILE_COLS} tiles')
        
        print(f'\n  ✓ Variable {var_name} complete')
        print(f'    Files:  {metadata["variables"][var_name]["file_count"]}')
        print(f'    Size: {metadata["variables"][var_name]["total_size_mb"]:.2f} MB')
    
    # Save metadata
    metadata_file = os.path.join(OUTPUT_DIR, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f'\n{"="*70}')
    print('✓ GENERATION COMPLETE')
    print(f'{"="*70}')
    print(f'Metadata saved to: {metadata_file}')
    print(f'\nStatistics:')
    print(f'  - Total days: {len(dates_to_times)}')
    print(f'  - Total hours: {len(times)}')
    print(f'  - Total files: {total_files}')
    print(f'  - Total size: {total_size_mb:.2f} MB')
    print(f'  - Avg file size: {total_size_mb/total_files:.3f} MB')
    print(f'  - Tiles per hour: {TILE_ROWS * TILE_COLS}')
    print(f'\nOutput directory: {OUTPUT_DIR}/')


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - GeoJSON Generator')
    print(f'Version 1.2: Tiled ({TILE_ROWS}×{TILE_COLS} grid)')
    print('=' * 70)
    
    # Load NetCDF files
    ds_wave, ds_weather_inst, ds_weather_accum = load_netcdf_files()
    if ds_wave is None:
        print('\n✗ Failed to load NetCDF files')
        return
    
    # Get target grid (weather grid)
    target_lat = ds_weather_inst['latitude'].values
    target_lon = ds_weather_inst['longitude']. values
    
    # Interpolate wave data
    interpolated_wave = interpolate_wave_to_weather_grid(ds_wave, target_lat, target_lon)
    
    # Generate tiled GeoJSON files
    generate_tiled_geojson_files(ds_wave, ds_weather_inst, ds_weather_accum, interpolated_wave)
    
    print('\n' + '=' * 70)
    print('Next step: Run A3_2_2_build_interactive_map_tiled. py')
    print('=' * 70)


if __name__ == '__main__':
    main()
