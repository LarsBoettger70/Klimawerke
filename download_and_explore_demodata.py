"""
Download REMO demo data from GitHub and explore it
Perfect for testing your analysis pipeline
"""

import os
import xarray as xr
import pandas as pd
import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import box
import urllib.request
import sys

# GitHub URLs for demo data
GITHUB_BASE = "https://raw.githubusercontent.com/remo-rcm/pyremo-data/main/"

DEMO_FILES = {
    'remo_eur44':  f"{GITHUB_BASE}remo_EUR-44.nc",  # Full EUR-44 domain
    'remo_temp2_monthly': f"{GITHUB_BASE}remo_EUR-11_TEMP2_mon.nc",  # Temperature data
    'remo_temp2_hourly': f"{GITHUB_BASE}remo_EUR-11_TEMP2_1hr.nc",  # Hourly data
}

def download_file(url, filename):
    """Download a file from GitHub with progress bar"""
    print(f"\nDownloading {filename}...")
    print(f"URL: {url}")
    
    try:
        def progress_hook(blocknum, blocksize, totalsize):
            downloaded = blocknum * blocksize
            percent = min(downloaded * 100 // totalsize, 100)
            sys.stdout.write(f'\r  Progress: {percent}%')
            sys.stdout.flush()
        
        urllib.request. urlretrieve(url, filename, progress_hook)
        print(f"\n✓ Downloaded {filename} ({os.path.getsize(filename) / 1024 / 1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"\n✗ Error downloading:   {e}")
        return False

def load_remo_data(filepath):
    """Load and explore REMO NetCDF file"""
    try:
        ds = xr.open_dataset(filepath)
        return ds
    except Exception as e: 
        print(f"Error loading {filepath}: {e}")
        return None

def print_dataset_info(ds, name="Dataset"):
    """Print detailed dataset information"""
    print(f"\n{'='*60}")
    print(f"DATASET: {name}")
    print(f"{'='*60}")
    
    print(f"\nDimensions:  {dict(ds.dims)}")
    print(f"\nCoordinates:")
    for coord in ds.coords:
        print(f"  - {coord}:  {ds[coord].shape} {ds[coord].dtype}")
    
    print(f"\nData Variables:")
    for var in ds.data_vars:
        attrs = ds[var].attrs
        units = attrs.get('units', 'N/A')
        long_name = attrs.get('long_name', 'N/A')
        print(f"  - {var}: {ds[var].shape}")
        print(f"      units: {units}, long_name: {long_name}")
    
    print(f"\nGlobal Attributes:")
    for key, value in ds.attrs.items():
        if len(str(value)) < 80:
            print(f"  {key}: {value}")

def extract_germany(ds):
    """Extract Germany region from REMO EUR-44 or EUR-11 data"""
    print(f"\n{'='*60}")
    print("EXTRACTING GERMANY REGION")
    print(f"{'='*60}")
    
    # Check coordinate system
    if 'rlon' in ds.coords and 'rlat' in ds.coords:
        print("\n✓ Dataset uses rotated coordinates (rlon, rlat)")
        print("  This is typical for REMO output")
        print(f"  rlon range: {float(ds.rlon.min()):.2f} to {float(ds.rlon.max()):.2f}")
        print(f"  rlat range: {float(ds. rlat.min()):.2f} to {float(ds. rlat.max()):.2f}")
        
        # REMO EUR-44 covers all of Europe, including Germany
        # Germany is roughly in the center
        # For now, we'll take a slice
        print("\n  Germany is contained within this rotated grid")
        print("  Taking center slice to represent Germany...")
        
        # Get approximate center indices
        rlon_center_idx = len(ds.rlon) // 2
        rlat_center_idx = len(ds.rlat) // 2
        window = 50  # 50 grid points on each side
        
        germany_subset = ds. isel(
            rlon=slice(max(0, rlon_center_idx - window), rlon_center_idx + window),
            rlat=slice(max(0, rlat_center_idx - window), rlat_center_idx + window)
        )
        
        print(f"\n✓ Extracted subset with shape: {dict(germany_subset.dims)}")
        return germany_subset
    
    elif 'lat' in ds.coords and 'lon' in ds.coords:
        print("\n✓ Dataset uses standard lat/lon coordinates")
        # Germany bounds (approx)
        lat_min, lat_max = 47.3, 55.5
        lon_min, lon_max = 5.5, 16.0
        
        germany = ds.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )
        print(f"✓ Extracted Germany region")
        print(f"  Lat:  {lat_min} to {lat_max}")
        print(f"  Lon: {lon_min} to {lon_max}")
        print(f"  Subset shape: {dict(germany.dims)}")
        return germany
    
    else:
        print(f"✗ Unexpected coordinate system:  {list(ds.coords)}")
        return ds

def create_visualization(ds, filename_output="remo_data_map.html"):
    """Create interactive map of REMO data"""
    print(f"\n{'='*60}")
    print("CREATING VISUALIZATION")
    print(f"{'='*60}")
    
    # Germany center
    center = [51.1657, 10.4515]
    
    m = folium.Map(
        location=center,
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add Germany border (approximate)
    bounds = [[47.3, 5.5], [55.5, 16.0]]
    folium.Rectangle(
        bounds=bounds,
        color='red',
        fill=True,
        fillOpacity=0.1,
        weight=2,
        popup="Germany"
    ).add_to(m)
    
    # Add marker
    folium.Marker(
        location=center,
        popup="REMO EUR-44 Domain",
        icon=folium. Icon(color='blue', icon='info-sign')
    ).add_to(m)
    
    m.save(filename_output)
    print(f"\n✓ Map saved to '{filename_output}'")

def main():
    print("="*60)
    print("REMO DEMO DATA - Download & Exploration Tool")
    print("="*60)
    
    # Step 1: Download smallest demo file (EUR-44 domain)
    print("\n[1] Downloading REMO demo data from GitHub...")
    print("    This is a small EUR-44 domain file (~16 MB)")
    
    filename = "remo_EUR-44.nc"
    if not os.path.exists(filename):
        success = download_file(DEMO_FILES['remo_eur44'], filename)
        if not success:
            print("Failed to download.   You can manually download from:")
            print(f"  {DEMO_FILES['remo_eur44']}")
            return
    else:
        print(f"\n✓ File {filename} already exists")
    
    # Step 2: Load and explore the data
    print("\n[2] Loading REMO data...")
    ds = load_remo_data(filename)
    
    if ds is None:
        return
    
    print_dataset_info(ds, "REMO EUR-44")
    
    # Step 3: Extract Germany region
    print("\n[3] Extracting Germany region...")
    germany = extract_germany(ds)
    
    if germany is not None:
        print("\nGermany subset info:")
        print(germany)
        
        # Save to file
        germany.to_netcdf("remo_germany_subset.nc")
        print(f"\n✓ Saved Germany subset to 'remo_germany_subset.nc'")
    
    # Step 4: Create visualization
    print("\n[4] Creating visualization...")
    create_visualization(ds)
    
    # Step 5: Display sample data values
    print("\n[5] Sample data values:")
    if 'TEMP2' in ds.data_vars:
        temp = ds. TEMP2
        print(f"\nTemperature (TEMP2):")
        print(f"  Shape: {temp.shape}")
        print(f"  Min: {float(temp.min()):.2f} K")
        print(f"  Max: {float(temp.max()):.2f} K")
        print(f"  Mean: {float(temp.mean()):.2f} K")
    
    # Step 6: Save dataset info to file
    with open('remo_data_structure.txt', 'w') as f:
        f.write("REMO Demo Data Structure\n")
        f.write("="*60 + "\n")
        f.write(str(ds))
        f.write("\n\n")
        f.write("Germany Subset:\n")
        f.write(str(germany))
    
    print(f"\n✓ Dataset information saved to 'remo_data_structure.txt'")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("  1. Open 'remo_data_map.html' in your browser")
    print("  2. Review 'remo_data_structure. txt' for data details")
    print("  3. Check 'remo_germany_subset.nc' for extracted region")
    print("  4. Download monthly temperature file for more data:")
    print(f"     {DEMO_FILES['remo_temp2_monthly']}")
    print("="*60)

if __name__ == "__main__":
    main()