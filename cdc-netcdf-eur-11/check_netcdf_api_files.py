#!/usr/bin/env python3
'''
Inspect Downloaded CDS NetCDF Files
'''

import xarray as xr
import pandas as pd
import os
import glob

# Configuration
NETCDF_DIR = 'geojson_daily_netcdf'

# Find all downloaded NetCDF files
netcdf_files = sorted(glob.glob(os.path.join(NETCDF_DIR, '*.nc')))

if not netcdf_files:
    print(f"✗ No NetCDF files found in {NETCDF_DIR}/")
    print(f"  Download some data first using:  python3 geojson_daily.py --date-range 2025-12-01 2025-12-24")
    exit(1)

# Menu to select the file
print("="*70)
print("Available NetCDF files:")
print("="*70)

file_options = {}
for i, filepath in enumerate(netcdf_files, 1):
    filename = os.path.basename(filepath)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"{i}:   {filename} ({file_size_mb:.2f} MB)")
    file_options[str(i)] = filepath
    
print(f"\n{len(netcdf_files)} file(s) found")
print("="*70)

file_choice = input("\nSelect a file to analyze (number): ").strip()

if file_choice not in file_options:
    print("✗ Invalid choice! Please restart and select a valid option.")
    exit(1)

# Load the selected NetCDF file
NETCDF_FILE = file_options[file_choice]
filename = os.path.basename(NETCDF_FILE)
print(f"\n{'='*70}")
print(f"Analyzing:  {filename}")
print(f"{'='*70}\n")

try:
    ds = xr.open_dataset(NETCDF_FILE)
except Exception as e:
    print(f"✗ Error opening file: {e}")
    exit(1)

# Prepare the data structure output
output = []

output.append("="*70)
output.append(f"FILE: {filename}")
output.append("="*70)

output.append("\n=== FILE OVERVIEW ===\n")
output.append(str(ds))

output.append("\n=== DIMENSIONS ===\n")
output.append(str(ds.dims))

output.append("\n=== COORDINATES ===\n")
output.append(str(ds.coords))

output.append("\n=== DATA VARIABLES ===\n")
output.append(str(list(ds.data_vars)))

# Check which coordinate names are used
lat_coord = None
lon_coord = None
time_coord = None

for coord in ['latitude', 'lat', 'y']:
    if coord in ds.coords:
        lat_coord = coord
        break

for coord in ['longitude', 'lon', 'x']:
    if coord in ds.coords:
        lon_coord = coord
        break

for coord in ['valid_time', 'time', 't']:
    if coord in ds.coords:
        time_coord = coord
        break

if not lat_coord or not lon_coord:
    print("✗ Could not find latitude/longitude coordinates")
    ds.close()
    exit(1)

lat_values = ds[lat_coord].values
lon_values = ds[lon_coord].values

# Time info
if time_coord:
    time_values = ds[time_coord].values
    output.append(f"\n=== TIME INFORMATION ===\n")
    output.append(f"Time coordinate: {time_coord}")
    output.append(f"Number of time steps: {len(time_values)}")
    output.append(f"First time:  {pd.to_datetime(time_values[0])}")
    output.append(f"Last time: {pd.to_datetime(time_values[-1])}")

# Grid info
output.append(f"\n=== GRID INFORMATION ===\n")
output.append(f"Latitude: {len(lat_values)} points ({lat_values.min():.2f}° to {lat_values.max():.2f}°)")
output.append(f"Longitude: {len(lon_values)} points ({lon_values.min():.2f}° to {lon_values.max():.2f}°)")
output.append(f"Total grid points: {len(lat_values) * len(lon_values)}")

# Memory size
output.append(f"\n=== FILE SIZE ===\n")
file_size_mb = os.path.getsize(NETCDF_FILE) / (1024 * 1024)
memory_size_mb = ds.nbytes / (1024 * 1024)
output.append(f"On disk: {file_size_mb:.2f} MB")
output.append(f"In memory (uncompressed): {memory_size_mb:.2f} MB")
output.append(f"Compression ratio: {memory_size_mb / file_size_mb:.1f}x")

# Sample grid points
rows = []
max_points = 20
output.append(f"\n=== SAMPLE GRID POINTS (first {max_points}) ===\n")

time_idx = 0  # First time step

for i in range(min(max_points, len(lat_values) * len(lon_values))):
    iy = i // len(lon_values)
    ix = i % len(lon_values)

    row = {
        "gridy": iy,
        "gridx": ix,
        lat_coord: float(lat_values[iy]),
        lon_coord: float(lon_values[ix]),
    }

    # Extract variables
    for var in ds.data_vars:
        try:
            if time_coord and time_coord in ds[var].dims:
                value = ds[var].isel({time_coord: time_idx, lat_coord: iy, lon_coord: ix}).values
            else:
                value = ds[var].isel({lat_coord: iy, lon_coord:  ix}).values
            row[var] = float(value) if value.size > 0 else None
        except Exception:
            row[var] = None

    rows.append(row)

# Create DataFrame
df_sample = pd.DataFrame(rows)
output.append(df_sample.to_string(index=False))

# Variable statistics
output.append(f"\n=== VARIABLE STATISTICS (first time step) ===\n")
for var in ds.data_vars:
    try:
        if time_coord and time_coord in ds[var].dims:
            data = ds[var].isel({time_coord: time_idx}).values
        else:
            data = ds[var].values
        
        output.append(f"\n{var}:")
        output.append(f"  Min: {data.min():.4f}")
        output.append(f"  Max: {data.max():.4f}")
        output.append(f"  Mean: {data.mean():.4f}")
        output.append(f"  NaN count: {pd.isna(data).sum()}")
    except Exception as e:
        output.append(f"\n{var}: Error - {e}")

# Close dataset
ds.close()

# Save output
output_filename = f"inspection_{filename[:-3]}.txt"
with open(output_filename, "w") as file:
    file.write("\n".join(output))

# Display
print("\n".join(output))
print(f"\n{'='*70}")
print(f"✓ Analysis saved to: {output_filename}")
print(f"{'='*70}\n")
