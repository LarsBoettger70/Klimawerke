#!/usr/bin/env python3
'''
Convert CDS ERA5 NetCDF files to GeoJSON
Handles merged NetCDF files with all variables
'''

import xarray as xr
import json
import os
import glob
from datetime import datetime

# Configuration
INPUT_DIR = 'geojson_daily_netcdf'
OUTPUT_DIR = 'geojson_daily'

# Variable mapping (NetCDF name -> GeoJSON property name)
VARIABLE_MAPPING = {
    'tp': 'precipitation',           # Total precipitation (m)
    'u10': 'wind_u',                 # 10m U-wind component (m/s)
    'v10': 'wind_v',                 # 10m V-wind component (m/s)
    't2m': 'temperature',            # 2m temperature (K)
    'swh': 'wave_height',            # Significant wave height (m)
    'sst': 'sea_surface_temp'        # Sea surface temperature (K)
}


def netcdf_to_geojson(netcdf_file, output_dir):
    '''Convert single NetCDF file to daily GeoJSON files (one per hour)'''
    
    print(f'\nProcessing: {os.path.basename(netcdf_file)}')
    
    try:
        # Open dataset
        ds = xr.open_dataset(netcdf_file, engine='netcdf4')
        
        # Get date from filename (era5_central_europe_YYYY-MM-DD.nc)
        filename = os.path.basename(netcdf_file)
        date_str = filename.split('_')[-1].replace('.nc', '')
        
        print(f'  Date: {date_str}')
        print(f'  Variables: {list(ds.data_vars.keys())}')
        print(f'  Time steps: {len(ds.valid_time)}')
        print(f'  Grid: {len(ds.latitude)} × {len(ds.longitude)} = {len(ds.latitude) * len(ds.longitude)} points')
        
        # Create output directory for this date
        date_output_dir = os.path.join(output_dir, date_str)
        os.makedirs(date_output_dir, exist_ok=True)
        
        # Process each hour
        for time_idx in range(len(ds.valid_time)):
            time_value = ds.valid_time.values[time_idx]
            time_dt = datetime.fromisoformat(str(time_value).replace('T', ' ').split('.')[0])
            hour = time_dt.hour
            
            features = []
            
            # Loop through all grid points
            for lat_idx in range(len(ds.latitude)):
                for lon_idx in range(len(ds.longitude)):
                    lat = float(ds.latitude.values[lat_idx])
                    lon = float(ds.longitude.values[lon_idx])
                    
                    # Extract values for this point
                    properties = {
                        'date': date_str,
                        'hour': hour,
                        'latitude': lat,
                        'longitude': lon
                    }
                    
                    # Add all variables
                    for nc_var, geo_var in VARIABLE_MAPPING.items():
                        if nc_var in ds.data_vars:
                            value = ds[nc_var].isel(valid_time=time_idx, latitude=lat_idx, longitude=lon_idx).values
                            # Convert to Python float, handle NaN
                            properties[geo_var] = float(value) if not pd.isna(value) else None
                    
                    # Create GeoJSON feature
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [lon, lat]
                        },
                        'properties': properties
                    }
                    
                    features.append(feature)
            
            # Create GeoJSON FeatureCollection
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            # Save to file
            output_file = os.path.join(date_output_dir, f'{date_str}_hour_{hour:02d}.geojson')
            with open(output_file, 'w') as f:
                json.dump(geojson, f)
            
            print(f'  ✓ Hour {hour:02d}: {len(features)} features -> {output_file}')
        
        ds.close()
        print(f'✓ Completed: {date_str}')
        
    except Exception as e:
        print(f'✗ Error processing {netcdf_file}: {e}')
        return False
    
    return True


def main():
    '''Process all NetCDF files in input directory'''
    
    print('='*70)
    print('CDS NetCDF to GeoJSON Converter')
    print('='*70)
    
    # Find all NetCDF files
    netcdf_files = sorted(glob.glob(os.path.join(INPUT_DIR, 'era5_central_europe_*.nc')))
    
    if not netcdf_files:
        print(f'\n✗ No NetCDF files found in {INPUT_DIR}/')
        return
    
    print(f'\nFound {len(netcdf_files)} NetCDF file(s)')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Process each file
    successful = 0
    failed = 0
    
    for netcdf_file in netcdf_files:
        if netcdf_to_geojson(netcdf_file, OUTPUT_DIR):
            successful += 1
        else:
            failed += 1
    
    print(f'\n{"="*70}')
    print(f'Conversion Complete!')
    print(f'{"="*70}')
    print(f'  ✓ Successful: {successful}')
    print(f'  ✗ Failed: {failed}')
    print(f'  Output directory: {OUTPUT_DIR}/')
    print(f'{"="*70}\n')


if __name__ == '__main__':
    import pandas as pd  # For NaN handling
    main()
