"""
REMO Climate Model - Final Visualization
Creates interactive map with polygons and parameter table
"""

import xarray as xr
import pandas as pd
import folium
from folium import plugins
import geopandas as gpd
from shapely.geometry import box, Polygon
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os

def load_remo_data(filepath):
    """Load REMO NetCDF file"""
    print(f"Loading {filepath}...")
    try:
        ds = xr. open_dataset(filepath)
        print(f"✓ Loaded successfully")
        return ds
    except Exception as e:
        print(f"✗ Error:  {e}")
        return None

def extract_grid_points(ds, region_name='Germany'):
    """
    Extract grid points and create coordinate dataframe
    Handles both standard and rotated coordinates
    """
    print(f"\n[1] Extracting {region_name} grid points...")
    
    data = []
    
    if 'rlon' in ds.coords and 'rlat' in ds.coords:
        # Rotated coordinates (REMO native)
        print("  Using rotated coordinates (rlon, rlat)")
        
        rlon = ds.rlon.values
        rlat = ds.rlat.values
        
        # Create meshgrid of coordinates
        for i, lat in enumerate(rlat):
            for j, lon in enumerate(rlon):
                data.append({
                    'grid_y': i,
                    'grid_x': j,
                    'rlat': float(lat),
                    'rlon': float(lon),
                    'lat': float(lat) + 40,  # Rough conversion
                    'lon': float(lon) + 10,  # Rough conversion
                })
    
    elif 'lat' in ds.coords and 'lon' in ds.coords:
        # Standard lat/lon coordinates
        print("  Using standard lat/lon coordinates")
        
        lat = ds.lat.values
        lon = ds.lon.values
        
        for i, la in enumerate(lat):
            for j, lo in enumerate(lon):
                data.append({
                    'grid_y': i,
                    'grid_x':  j,
                    'lat': float(la),
                    'lon': float(lo),
                })
    
    df = pd.DataFrame(data)
    print(f"✓ Extracted {len(df)} grid points")
    
    return df

def create_grid_polygons(coord_df, cell_size=0.5):
    """
    Create polygon for each grid cell
    """
    print(f"\n[2] Creating grid polygons (cell size: {cell_size}°)...")
    
    polygons = []
    
    for idx, row in coord_df.iterrows():
        lat = row['lat']
        lon = row['lon']
        
        # Create square polygon around each point
        half_size = cell_size / 2
        poly = box(
            lon - half_size,
            lat - half_size,
            lon + half_size,
            lat + half_size
        )
        
        polygons.append({
            'grid_x': row['grid_x'],
            'grid_y': row['grid_y'],
            'lat': lat,
            'lon':  lon,
            'geometry': poly
        })
    
    gdf = gpd.GeoDataFrame(polygons, crs='EPSG:4326')
    print(f"✓ Created {len(gdf)} polygons")
    
    return gdf

def extract_climate_parameters(ds, coord_df):
    """
    Extract temperature and other parameters for each location
    """
    print(f"\n[3] Extracting climate parameters...")
    
    params = []
    
    for idx, row in coord_df.iterrows():
        grid_x = int(row['grid_x'])
        grid_y = int(row['grid_y'])
        
        param_dict = {
            'grid_x': grid_x,
            'grid_y': grid_y,
            'lat': round(row['lat'], 2),
            'lon': round(row['lon'], 2),
        }
        
        # Extract variables based on what's available
        if 'TEMP2' in ds.data_vars:
            try:
                # Get first time step
                temp_val = float(ds. TEMP2.isel(rlon=grid_x, rlat=grid_y).values[0])
                param_dict['TEMP2_K'] = round(temp_val, 2)
                param_dict['TEMP2_C'] = round(temp_val - 273.15, 2)
            except: 
                param_dict['TEMP2_K'] = None
                param_dict['TEMP2_C'] = None
        
        if 'APRL' in ds.data_vars or 'APRC' in ds.data_vars:
            try:
                aprl = float(ds.APRL. isel(rlon=grid_x, rlat=grid_y).values[0]) if 'APRL' in ds.data_vars else 0
                aprc = float(ds.APRC.isel(rlon=grid_x, rlat=grid_y).values[0]) if 'APRC' in ds.data_vars else 0
                param_dict['PRECIP'] = round(aprl + aprc, 4)
            except:
                param_dict['PRECIP'] = None
        
        params.append(param_dict)
    
    df_params = pd.DataFrame(params)
    print(f"✓ Extracted parameters for {len(df_params)} points")
    
    return df_params

def create_interactive_map(gdf, params_df, output_file='remo_interactive_map.html'):
    """
    Create interactive map with polygons and popups
    """
    print(f"\n[4] Creating interactive map...")
    
    # Calculate center
    center_lat = gdf. geometry.centroid. y. mean()
    center_lon = gdf.geometry.centroid. x.mean()
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles='OpenStreetMap'
    )
    
    # Add polygons with popups
    for idx, (geom_idx, geom_row) in enumerate(gdf.iterrows()):
        if idx % 100 == 0:
            print(f"  Adding polygons...  {idx}/{len(gdf)}")
        
        # Get corresponding parameter data
        param_row = params_df.iloc[geom_idx]
        
        # Create popup text
        popup_text = f"""
        <b>Grid Point</b><br>
        Lat: {param_row['lat']:.2f}°<br>
        Lon: {param_row['lon']:.2f}°<br>
        """
        
        if 'TEMP2_C' in param_row and pd.notna(param_row['TEMP2_C']):
            popup_text += f"Temp: {param_row['TEMP2_C']:.1f}°C<br>"
        
        if 'PRECIP' in param_row and pd.notna(param_row['PRECIP']):
            popup_text += f"Precip: {param_row['PRECIP']:.2f} mm<br>"
        
        # Add polygon to map
        folium.GeoJson(
            geom_row. geometry.__geo_interface__,
            style_function=lambda x, idx=idx: {
                'color': 'blue',
                'weight': 1,
                'opacity': 0.5,
                'fillOpacity': 0.1
            },
            popup=folium. Popup(popup_text, max_width=200)
        ).add_to(m)
    
    # Add Germany border
    germany_bounds = [[47.3, 5.5], [55.5, 16.0]]
    folium.Rectangle(
        bounds=germany_bounds,
        color='red',
        fill=False,
        weight=2,
        popup="Germany Border"
    ).add_to(m)
    
    m.save(output_file)
    print(f"✓ Map saved to '{output_file}'")
    
    return m

def create_parameter_table(params_df, output_file='climate_parameters_table.html'):
    """
    Create HTML table of climate parameters
    """
    print(f"\n[5] Creating parameter table...")
    
    # Select columns to display
    display_cols = ['lat', 'lon']
    if 'TEMP2_C' in params_df.columns:
        display_cols.append('TEMP2_C')
    if 'PRECIP' in params_df.columns:
        display_cols.append('PRECIP')
    
    # Get top 20 points
    table_df = params_df[display_cols].head(20).copy()
    
    # Rename columns for display - only rename the columns that exist
    new_names = ['Latitude', 'Longitude']
    if 'TEMP2_C' in table_df.columns:
        new_names.append('Temperature (°C)')
    if 'PRECIP' in table_df.columns:
        new_names.append('Precipitation (mm)')
    
    table_df.columns = new_names
    
    # Create HTML
    html = """
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align:  left;
            }}
            th {{
                background-color: #4CAF50;
                color:  white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #ddd;
            }}
            h1 {{
                color: #333;
            }}
        </style>
    </head>
    <body>
        <h1>REMO Climate Model - Parameter Table</h1>
        <p>Sample of {0} grid points from Germany region</p>
        {1}
    </body>
    </html>
    """.format(len(params_df), table_df.to_html(index=False))
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✓ Table saved to '{output_file}'")

def create_summary_report(ds, coord_df, params_df):
    """
    Create text summary report
    """
    print(f"\n[6] Creating summary report...")
    
    report = f"""
{'='*60}
REMO CLIMATE MODEL ANALYSIS - SUMMARY REPORT
{'='*60}

DATASET INFORMATION:
  Time steps: {len(ds. time) if 'time' in ds. dims else 'N/A'}
  Grid dimensions: {dict(ds.dims)}
  Variables: {list(ds.data_vars)}

EXTRACTED REGION:  Germany
  Total grid points: {len(coord_df)}
  Lat range: {coord_df['lat'].min():.2f}° - {coord_df['lat'].max():.2f}°
  Lon range: {coord_df['lon'].min():.2f}° - {coord_df['lon'].max():.2f}°

CLIMATE PARAMETERS: 
"""
    
    if 'TEMP2_C' in params_df.columns:
        report += f"""  Temperature (°C):
    Min: {params_df['TEMP2_C'].min():.2f}°C
    Max:  {params_df['TEMP2_C'].max():.2f}°C
    Mean: {params_df['TEMP2_C'].mean():.2f}°C
"""
    
    if 'PRECIP' in params_df. columns:
        report += f"""  Precipitation (mm):
    Min: {params_df['PRECIP'].min():.4f} mm
    Max: {params_df['PRECIP'].max():.4f} mm
    Mean: {params_df['PRECIP'].mean():.4f} mm
"""
    
    report += f"""
OUTPUT FILES CREATED:
  - remo_interactive_map. html (Interactive map with polygons)
  - climate_parameters_table.html (Parameter table)
  - climate_parameters. csv (Full parameter data)
  - analysis_report.txt (This report)

{'='*60}
"""
    
    with open('analysis_report.txt', 'w') as f:
        f.write(report)
    
    # Also save parameters to CSV
    params_df. to_csv('climate_parameters. csv', index=False)
    
    print(report)
    print(f"✓ Report saved to 'analysis_report. txt'")
    print(f"✓ Parameters saved to 'climate_parameters. csv'")

def main():
    print("="*60)
    print("REMO Climate Model - Complete Visualization Pipeline")
    print("="*60)
    
    # Check if data file exists
    if not os.path.exists('remo_EUR-44.nc'):
        print("\n✗ Error: remo_EUR-44.nc not found")
        print("  Run 'python3 download_and_explore_data.py' first")
        return
    
    # Load data
    ds = load_remo_data('remo_EUR-44.nc')
    if ds is None:
        return
    
    # Extract grid points
    coord_df = extract_grid_points(ds, 'Germany')
    
    # Create polygons (sample - use fewer points for performance)
    print("\n  Note: Using sample of grid points for visualization")
    coord_sample = coord_df.iloc[:: 10]  # Every 10th point
    gdf = create_grid_polygons(coord_sample, cell_size=0.5)
    
    # Extract parameters
    params_df = extract_climate_parameters(ds, coord_df)
    
    # Create visualizations
    create_interactive_map(gdf, params_df)
    create_parameter_table(params_df)
    
    # Create report
    create_summary_report(ds, coord_df, params_df)
    
    print("\n" + "="*60)
    print("✓ VISUALIZATION COMPLETE!")
    print("="*60)
    print("\nOutput files created:")
    print("  1. remo_interactive_map. html - Open in browser!")
    print("  2. climate_parameters_table.html - View parameters")
    print("  3. climate_parameters.csv - All data in CSV format")
    print("  4. analysis_report.txt - Summary statistics")
    print("="*60)
    print("\nNext steps:")
    print("  1. open remo_interactive_map.html")
    print("  2. open climate_parameters_table.html")
    print("  3. Review climate_parameters.csv in spreadsheet")
    print("="*60)

if __name__ == "__main__":
    main()