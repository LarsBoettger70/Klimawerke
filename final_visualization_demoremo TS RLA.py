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
import numpy as np

NETCDF_FILE = "remo_germany_subset.nc"
#remo_EUR-44.nc / remo_germany_subset.nc

def rotated_to_geo(rlon, rlat, pole_lon, pole_lat):
    """
    abs. pole koord.: rotated_to_geo(rlon, rlat, pole_lon=-162.0, pole_lat=39.25):
    
    aus datei: pole_lon = float(ds.rotated_pole.grid_north_pole_longitude)
    pole_lat = float(ds.rotated_pole.grid_north_pole_latitude)

    Wandelt REMO-rotated-pole-Koordinaten (rlon, rlat in Grad)
    in geografische Koordinaten (lon, lat in Grad) um.
    Die Default-Werte von pole_lon/pole_lat sind typische REMO-EUR-44-Einstellungen –
    ggf. mit den Attributen im NetCDF abgleichen (ds.rotated_pole.grid_north_pole_longitude/-latitude).
    """
    # Grad -> Radiant
    rlon_rad = np.deg2rad(rlon)
    rlat_rad = np.deg2rad(rlat)
    pol_lon_rad = np.deg2rad(pole_lon)
    pol_lat_rad = np.deg2rad(pole_lat)

    # Formeln für "rotated_pole" (CF-konventionell)
    sin_lat = (np.sin(pol_lat_rad) * np.sin(rlat_rad) +
               np.cos(pol_lat_rad) * np.cos(rlat_rad) * np.cos(rlon_rad))
    lat = np.arcsin(sin_lat)

    y = (-np.cos(rlat_rad) * np.sin(rlon_rad))
    x = (np.cos(pol_lat_rad) * np.sin(rlat_rad) -
         np.sin(pol_lat_rad) * np.cos(rlat_rad) * np.cos(rlon_rad))
    lon = pol_lon_rad + np.arctan2(y, x)

    # Radiant -> Grad, Längengrad auf [-180, 180] bringen
    lat_deg = np.rad2deg(lat)
    lon_deg = (np.rad2deg(lon) + 540) % 360 - 180
    return lon_deg, lat_deg

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

def extract_grid_points(ds, regionname="Germany"):
    print("1) Extracting", regionname, "grid points...")
    data = []

    if "rlon" in ds.coords and "rlat" in ds.coords:
        print("   Using rotated coordinates (REMO native)...")
        rlon = ds.rlon.values
        rlat = ds.rlat.values

        # Polkoordinaten aus Attributen holen, falls vorhanden
        pole_lon = float(ds.rotated_pole.grid_north_pole_longitude)
        pole_lat = float(ds.rotated_pole.grid_north_pole_latitude)

        for i, rla in enumerate(rlat):
            for j, rlo in enumerate(rlon):
                lon_deg, lat_deg = rotated_to_geo(rlo, rla, pole_lon=pole_lon, pole_lat=pole_lat)
                data.append({
                    "gridy": i,
                    "gridx": j,
                    "rlat": float(rla),
                    "rlon": float(rlo),
                    "lat": float(lat_deg),
                    "lon": float(lon_deg),
                })

    elif "lat" in ds.coords and "lon" in ds.coords:
        print("   Using standard lat/lon coordinates...")
        lat = ds.lat.values
        lon = ds.lon.values
        for i, la in enumerate(lat):
            for j, lo in enumerate(lon):
                data.append({"gridy": i, "gridx": j, "lat": float(la), "lon": float(lo)})
    else:
        raise ValueError("No suitable coordinate system (rlon/rlat or lat/lon) found in dataset.")

    df = pd.DataFrame(data)
    print("   Extracted", len(df), "grid points.")
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
            'gridx': row['gridx'],
            'gridy': row['gridy'],
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
        grid_x = int(row['gridx'])
        grid_y = int(row['gridy'])
        
        param_dict = {
            'gridx': grid_x,
            'gridy': grid_y,
            'lat': round(row['lat'], 2),
            'lon': round(row['lon'], 2),
        }
        
        # Surface temperature als „Temperatur“ nutzen
        if 'TS' in ds.data_vars:
            try:
                # Get first time step
                temp_val = float(ds["TS"].isel(time=0, rlon=grid_x, rlat=grid_y).values)
                param_dict['TS_K'] = round(temp_val, 2)
                param_dict['TS_C'] = round(temp_val - 273.15, 2)
            except Exception:
                param_dict['TS_K'] = None
                param_dict['TS_C'] = None
        
        if 'RLA' in ds.data_vars:
            try:
                rla_val = float(ds['RLA'].isel(time=0, rlon=grid_x, rlat=grid_y).values)
                param_dict['RLA_Wm2'] = round(rla_val, 2)
            except Exception:
                param_dict['RLA_Wm2'] = None

        if 'APRL' in ds.data_vars or 'APRC' in ds.data_vars:
            try:
                aprl = float(ds['APRL'].isel(time=0, rlon=grid_x, rlat=grid_y).values) if 'APRL' in ds.data_vars else 0
                aprc = float(ds['APRC'].isel(time=0, rlon=grid_x, rlat=grid_y).values) if 'APRC' in ds.data_vars else 0
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

        if "TS_C" in param_row and pd.notna(param_row["TS_C"]):
            popup_text += f"Temp: {param_row['TS_C']:.1f} °C<br>"

        if "RLA_Wm2" in param_row and pd.notna(param_row["RLA_Wm2"]):
            popup_text += f"RLA: {param_row['RLA_Wm2']:.1f} W/m²<br>"

        if "PRECIP" in param_row and pd.notna(param_row["PRECIP"]):
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
    if 'TS_C' in params_df.columns:
        display_cols.append('TS_C')
    if 'RLA_Wm2' in params_df.columns:
        display_cols.append('RLA_Wm2')
    if 'PRECIP' in params_df.columns:
        display_cols.append('PRECIP')
    
    # Get top 20 points
    table_df = params_df[display_cols].head(20).copy()
    
    # Rename columns for display - only rename the columns that exist
    new_names = ['Latitude', 'Longitude']
    if 'TS_C' in table_df.columns:
        new_names.append('Temperature (°C)')
    if 'RLA_Wm2' in table_df.columns:
        new_names.append('Radiation (W/m²)')
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
    """Create text summary report"""
    print(f"\n[6] Creating summary report...")

    # Deutschland-Filter
    coord_df_DE = coord_df.query(
        "lat >= 47.3 and lat <= 55.5 and lon >= 5.5 and lon <= 16.0"
    )

    report = f"""
{'='*60}
REMO CLIMATE MODEL ANALYSIS - SUMMARY REPORT
{'='*60}

DATASET INFORMATION:
  Time steps: {len(ds.time) if 'time' in ds.dims else 'N/A'}
  Grid dimensions: {dict(ds.dims)}
  Variables: {list(ds.data_vars)}

EXTRACTED REGION: Germany
  Total grid points (all): {len(coord_df)}
  Total grid points (DE-filter): {len(coord_df_DE)}
  Lat range (DE-filter): {coord_df_DE['lat'].min():.2f}° - {coord_df_DE['lat'].max():.2f}°
  Lon range (DE-filter): {coord_df_DE['lon'].min():.2f}° - {coord_df_DE['lon'].max():.2f}°

CLIMATE PARAMETERS:
"""
    if 'TS_C' in params_df.columns:
        report += f"""
  Temperature (°C):
    Min:  {params_df['TS_C'].min():.2f}°C
    Max:  {params_df['TS_C'].max():.2f}°C
    Mean: {params_df['TS_C'].mean():.2f}°C
"""
    if "RLA_Wm2" in params_df.columns:
        report += f"""
  Longwave radiation (W/m²):
    Min:  {params_df['RLA_Wm2'].min():.2f} W/m²
    Max:  {params_df['RLA_Wm2'].max():.2f} W/m²
    Mean: {params_df['RLA_Wm2'].mean():.2f} W/m²
"""
    if 'PRECIP' in params_df.columns:
        report += f"""
  Precipitation (mm):
    Min:  {params_df['PRECIP'].min():.4f} mm
    Max:  {params_df['PRECIP'].max():.4f} mm
    Mean: {params_df['PRECIP'].mean():.4f} mm
"""

    report += f"""
OUTPUT FILES CREATED:
  - remo_interactive_map.html (Interactive map with polygons)
  - climate_parameters_table.html (Parameter table)
  - climate_parameters.csv (Full parameter data)
  - analysis_report.txt (This report)

{'='*60}
"""

    with open('analysis_report.txt', 'w') as f:
        f.write(report)

    # Also save parameters to CSV
    params_df.to_csv('climate_parameters.csv', index=False)

    print(report)
    print("✓ Report saved to 'analysis_report.txt'")
    print("✓ Parameters saved to 'climate_parameters.csv'")

def main():
    print("="*60)
    print("REMO Climate Model - Complete Visualization Pipeline")
    print("="*60)

    # Check if data file exists
    if not os.path.exists(NETCDF_FILE):
        print(f"\n✗ Error: {NETCDF_FILE} not found")
        print(" Run 'python3 download_and_explore_data.py' first")
        return

    # Load data
    ds = load_remo_data(NETCDF_FILE)
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
