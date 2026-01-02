#!/usr/bin/env python3
'''
Daily CDS Data Downloader
Automatically downloads yesterday's ERA5 data for Central Europe
'''

import cdsapi
import os
from datetime import datetime, timedelta
import sys
import time

# Configuration
OUTPUT_DIR = 'geojson_daily_netcdf'
AREA = [55, 5, 47, 15]  # North, West, South, East (Central Europe)

# Variables to download
VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "sea_surface_temperature",
    "significant_height_of_combined_wind_waves_and_swell",
    "total_precipitation"
]

# All 24 hours
HOURS = [f"{h:02d}:00" for h in range(24)]

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
MIN_FILE_SIZE_MB = 0.1  # Minimum acceptable file size

def download_with_retry(client, dataset, request, output_file, max_retries=MAX_RETRIES):
    '''Download with retry logic'''
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f'\n{"Attempt " + str(attempt) if attempt > 1 else "Submitting request"}...')
            client.retrieve(dataset, request, output_file)
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for specific error types
            if "400" in error_msg and "not available yet" in error_msg:
                print(f'\n✗ Data not available yet')
                return False
                
            elif "400" in error_msg and "straddles" in error_msg:
                print(f'\n✗ Partial data only - try earlier date')
                return False
                
            elif "401" in error_msg or "403" in error_msg:
                print(f'\n✗ Authentication error - check your API key')
                print(f'   Make sure ~/.cdsapirc is configured correctly')
                return False
                
            elif "429" in error_msg:
                print(f'\n⚠ Rate limit hit - waiting {RETRY_DELAY}s before retry...')
                time.sleep(RETRY_DELAY)
                
            elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
                print(f'\n⚠ Server error - attempt {attempt}/{max_retries}')
                if attempt < max_retries:
                    print(f'   Waiting {RETRY_DELAY}s before retry...')
                    time.sleep(RETRY_DELAY)
                    
            else:
                print(f'\n✗ Error:  {error_msg}')
                if attempt < max_retries:
                    print(f'   Retrying in {RETRY_DELAY}s... ({attempt}/{max_retries})')
                    time.sleep(RETRY_DELAY)
    
    return False


def extract_and_merge_zip(zip_filepath, date_str):
    '''Extract zipped NetCDF files and merge them by date'''
    import zipfile
    import xarray as xr
    
    try:
        if not zipfile.is_zipfile(zip_filepath):
            return False
            
        print(f'  ℹ File is zipped, extracting and merging...')
        
        extract_dir = os.path.dirname(zip_filepath)
        temp_dir = os.path.join(extract_dir, f'temp_{date_str}')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract all files to temp directory
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find all extracted NetCDF files
        nc_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.nc')]
        
        if not nc_files:
            print(f'  ✗ No NetCDF files found in archive')
            return False
        
        # Merge all NetCDF files into one
        print(f'  ℹ Merging {len(nc_files)} files...')
        datasets = []
        for nc_file in nc_files:
            try:
                ds = xr.open_dataset(nc_file, engine='netcdf4')
                datasets.append(ds)
            except Exception as e:
                print(f'  ⚠ Could not open {os.path.basename(nc_file)}: {e}')
        
        if not datasets:
            print(f'  ✗ Could not open any NetCDF files')
            return False
        
        # Merge datasets
        merged_ds = xr.merge(datasets, compat='override', join='outer')
        
        # Save merged dataset
        final_output = zip_filepath.replace('.nc', '_merged.nc')
        merged_ds.to_netcdf(final_output)
        merged_ds.close()
        
        # Close all datasets
        for ds in datasets:
            ds.close()
        
        # Cleanup
        for nc_file in nc_files:
            os.remove(nc_file)
        os.rmdir(temp_dir)
        os.remove(zip_filepath)
        
        # Rename merged file to original name
        os.rename(final_output, zip_filepath)
        
        print(f'  ✓ Merged into single file')
        return True
        
    except Exception as e:
        print(f'  ✗ Extraction error: {e}')
        return False


def download_yesterday():
    '''Download data for latest available date (account for ERA5 delay)'''
    
    # Start with 6 days ago and work backwards if needed
    for days_back in range(6, 15):
        target_date = datetime.now() - timedelta(days=days_back)
        year = target_date.strftime('%Y')
        month = target_date.strftime('%m')
        day = target_date.strftime('%d')
        date_str = target_date.strftime('%Y-%m-%d')
        
        print(f'\n{"="*70}')
        print(f'CDS Daily Download')
        print(f'Trying date: {date_str} ({days_back} days ago)')
        print(f'{"="*70}')
        
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Output filename
        output_file = os.path.join(OUTPUT_DIR, f'era5_central_europe_{date_str}.nc')
        
        # Check if already downloaded
        if os.path.exists(output_file):
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f'✓ File already exists: {output_file}')
            print(f'✓ File size: {file_size_mb:.2f} MB')
            print('✓ Skipping download.')
            return
        
        # Build request
        dataset = "reanalysis-era5-single-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable": VARIABLES,
            "year": [year],
            "month": [month],
            "day": [day],
            "time": HOURS,
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area":  AREA
        }
        
        print(f'\nTarget:  {output_file}')
        print(f'Variables: {len(VARIABLES)}')
        print(f'Hours: 24')
        print(f'Area: {AREA}')
        
        try:
            # Initialize client
            client = cdsapi.Client()
            
            # Download with retry
            success = download_with_retry(client, dataset, request, output_file)
            
            if success:
                print(f'\n✓ Download complete!')
                print(f'✓ Saved to: {output_file}')
                
                # Extract and merge if zipped
                extract_and_merge_zip(output_file, date_str)
                
                # Check file size
                if os.path.exists(output_file):
                    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                    print(f'✓ Final file size: {file_size_mb:.2f} MB')
                    
                    # Validate file size
                    if file_size_mb < MIN_FILE_SIZE_MB:
                        print(f'⚠ Warning: File seems too small ({file_size_mb:.2f} MB)')
                        print(f'⚠ Download may be incomplete')
                        os.remove(output_file)
                        continue
                        
                return  # Success!
            else:
                print(f'⚠ Failed to download {date_str}, trying earlier date...')
                continue
                
        except KeyboardInterrupt:
            print(f'\n\n✗ Download interrupted by user')
            if os.path.exists(output_file):
                print(f'✗ Cleaning up partial file: {output_file}')
                os.remove(output_file)
            sys.exit(1)
            
        except Exception as e:
            print(f'\n✗ Unexpected error:  {e}')
            if os.path.exists(output_file):
                print(f'✗ Cleaning up partial file: {output_file}')
                os.remove(output_file)
            continue
    
    print(f'\n✗ Could not find available data in the last 15 days')
    print(f'✗ Latest attempt was:  {(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")}')
    sys.exit(1)


def download_date_range(start_date, end_date):
    '''Download data for a date range'''
    
    try:
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f'✗ Invalid date format: {e}')
        print(f'  Use YYYY-MM-DD format (e.g., 2025-12-01)')
        sys.exit(1)
    
    if current > end:
        print(f'✗ Start date must be before or equal to end date')
        sys.exit(1)
    
    total_days = (end - current).days + 1
    successful = 0
    failed = 0
    skipped = 0
    
    print(f'\n{"="*70}')
    print(f'CDS Batch Download')
    print(f'Date range: {start_date} to {end_date} ({total_days} days)')
    print(f'{"="*70}')
    
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        year = current.strftime('%Y')
        month = current.strftime('%m')
        day = current.strftime('%d')
        
        print(f'\n{"="*70}')
        print(f'Downloading: {date_str} ({successful + failed + skipped + 1}/{total_days})')
        print(f'{"="*70}')
        
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Output filename
        output_file = os.path.join(OUTPUT_DIR, f'era5_central_europe_{date_str}.nc')
        
        # Skip if exists
        if os.path.exists(output_file):
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f'✓ Already exists: {output_file}')
            print(f'✓ File size: {file_size_mb:.2f} MB')
            print(f'✓ Skipping...')
            skipped += 1
            current += timedelta(days=1)
            continue
        
        # Build request
        dataset = "reanalysis-era5-single-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable":  VARIABLES,
            "year":  [year],
            "month":  [month],
            "day":  [day],
            "time":  HOURS,
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area":  AREA
        }
        
        try:
            client = cdsapi.Client()
            success = download_with_retry(client, dataset, request, output_file)
            
            if success and os.path.exists(output_file):
                # Extract and merge if zipped
                extract_and_merge_zip(output_file, date_str)
                
                file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f'✓ Downloaded:  {file_size_mb:.2f} MB')
 
                # Validate file size
                if file_size_mb < MIN_FILE_SIZE_MB:
                    print(f'⚠ Warning: File seems too small, removing...')
                    os.remove(output_file)
                    failed += 1
                else:
                    successful += 1
            else:
                print(f'✗ Failed to download {date_str}')
                failed += 1
                
        except KeyboardInterrupt:
            print(f'\n\n✗ Batch download interrupted by user')
            print(f'\nSummary: ')
            print(f'  ✓ Successful: {successful}')
            print(f'  ✗ Failed: {failed}')
            print(f'  ⊘ Skipped: {skipped}')
            sys.exit(1)
            
        except Exception as e:
            print(f'✗ Unexpected error: {e}')
            if os.path.exists(output_file):
                os.remove(output_file)
            failed += 1
        
        current += timedelta(days=1)
        
        # Small delay between requests
        if current <= end:
            time.sleep(2)
    
    print(f'\n{"="*70}')
    print(f'Batch Download Complete!')
    print(f'{"="*70}')
    print(f'  ✓ Successful: {successful}/{total_days}')
    print(f'  ✗ Failed: {failed}/{total_days}')
    print(f'  ⊘ Skipped: {skipped}/{total_days}')
    print(f'{"="*70}\n')


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Download CDS ERA5 data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Download latest available: 
    python3 geojson_daily.py --yesterday
    
  Download specific date range:
    python3 geojson_daily.py --date-range 2025-12-01 2025-12-24
    
  Download single day: 
    python3 geojson_daily.py --date-range 2025-12-15 2025-12-15
        '''
    )
    
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                        help='Download date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--yesterday', action='store_true',
                        help='Download latest available data (default)')
    
    args = parser.parse_args()
    
    try:
        if args.date_range:
            download_date_range(args.date_range[0], args.date_range[1])
        else:
            download_yesterday()
    except KeyboardInterrupt:
        print(f'\n\n✗ Interrupted by user')
        sys.exit(1)
