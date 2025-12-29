"""
Polynomial Interpolation Demo for REMO Climate Data

This script demonstrates the complete workflow for downscaling REMO climate
model data using polynomial interpolation:
    1. Load REMO EUR-44 demo data
    2. Generate mesh over Germany
    3. Add synthetic weather stations
    4. Perform interpolation
    5. Create visualizations comparing original grid vs interpolated surface

Usage:
    python3 interpolation_demo.py
    
Output:
    - interpolation_demo_map.html: Interactive visualization
    - interpolation_results.csv: Interpolated values at mesh points
    - interpolation_quality_report.txt: Analysis of interpolation quality
"""

import os
import sys
import numpy as np
import pandas as pd
import xarray as xr
import folium
from folium import plugins
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import warnings
warnings.filterwarnings('ignore')

# Import our modules
from polynomial_interpolation import RemoInterpolator, calculate_interpolation_error, kelvin_to_celsius
from mesh_generator import (
    MeshGenerator, GermanyDomain, WeatherStationManager,
    CoordinateTransformer, extract_remo_grid_in_domain
)


def load_demo_data(filename='remo_germany_subset.nc'):
    """
    Load REMO demo data.
    
    Args:
        filename: NetCDF file path
    
    Returns:
        xarray Dataset
    """
    print(f"\n{'='*60}")
    print("STEP 1: Loading REMO Demo Data")
    print(f"{'='*60}")
    
    if not os.path.exists(filename):
        print(f"✗ Error: {filename} not found")
        print("  Please run 'python3 download_and_explore_demodata.py' first")
        sys.exit(1)
    
    ds = xr.open_dataset(filename)
    print(f"✓ Loaded {filename}")
    print(f"  Dimensions: {dict(ds.dims)}")
    print(f"  Variables: {list(ds.data_vars)[:10]}...")
    
    return ds


def setup_interpolation(ds, variable='TS', time_idx=0):
    """
    Set up interpolator for specified variable.
    
    Args:
        ds: REMO dataset
        variable: Variable to interpolate
        time_idx: Time index
    
    Returns:
        RemoInterpolator instance
    """
    print(f"\n{'='*60}")
    print("STEP 2: Setting Up Interpolator")
    print(f"{'='*60}")
    
    print(f"  Variable: {variable}")
    print(f"  Time index: {time_idx}")
    
    # Create interpolator
    interp = RemoInterpolator(
        ds,
        variable=variable,
        time_idx=time_idx,
        kernel='thin_plate_spline',
        neighbors=16
    )
    
    # Get statistics
    stats = interp.get_statistics()
    print(f"\n  Grid Statistics:")
    print(f"    Valid points: {stats['valid_points']}")
    
    # Convert temperature values to Celsius if the variable is TS (surface temperature)
    if variable == 'TS':
        value_min_c = kelvin_to_celsius(stats['value_min'])
        value_max_c = kelvin_to_celsius(stats['value_max'])
        value_mean_c = kelvin_to_celsius(stats['value_mean'])
        print(f"    Value range: {value_min_c:.2f}°C to {value_max_c:.2f}°C")
        print(f"    Mean value: {value_mean_c:.2f}°C")
    else:
        print(f"    Value range: {stats['value_min']:.2f} to {stats['value_max']:.2f}")
        print(f"    Mean value: {stats['value_mean']:.2f}")
    
    print(f"    rlat range: {stats['rlat_range']}")
    print(f"    rlon range: {stats['rlon_range']}")
    
    print(f"✓ Interpolator ready")
    
    return interp


def generate_mesh_and_stations(ds):
    """
    Generate mesh and weather stations for Germany.
    
    Args:
        ds: REMO dataset
    
    Returns:
        Tuple of (mesh_df, stations_df, grid_points_df)
    """
    print(f"\n{'='*60}")
    print("STEP 3: Generating Mesh and Stations")
    print(f"{'='*60}")
    
    # Define Germany domain
    domain = GermanyDomain()
    print(f"  Domain: {domain.name}")
    print(f"    Lat: {domain.lat_min}° to {domain.lat_max}°")
    print(f"    Lon: {domain.lon_min}° to {domain.lon_max}°")
    
    # Generate mesh (coarser resolution for demo)
    mesh_gen = MeshGenerator(domain)
    mesh = mesh_gen.generate_mesh(resolution=0.5)
    print(f"\n✓ Generated mesh with {len(mesh)} points")
    
    # Generate synthetic weather stations
    station_mgr = WeatherStationManager()
    stations = station_mgr.generate_synthetic_stations(domain, n_stations=10, seed=42)
    
    # Also add real German stations
    real_stations = station_mgr.get_german_reference_stations()
    print(f"✓ Added {len(stations)} synthetic stations")
    print(f"✓ Added {len(real_stations)} reference stations")
    
    all_stations = station_mgr.to_dataframe()
    
    # Extract REMO grid points in domain
    grid_points = extract_remo_grid_in_domain(ds, domain, use_phi_rla=True)
    print(f"✓ Extracted {len(grid_points)} REMO grid points in domain")
    
    return mesh, all_stations, grid_points


def perform_interpolation(interp, mesh, stations, grid_points, ds):
    """
    Perform interpolation at mesh and station points.
    
    Args:
        interp: RemoInterpolator instance
        mesh: Mesh DataFrame
        stations: Stations DataFrame
        grid_points: Grid points DataFrame
        ds: REMO dataset
    
    Returns:
        Tuple of (mesh_with_values, stations_with_values)
    """
    print(f"\n{'='*60}")
    print("STEP 4: Performing Interpolation")
    print(f"{'='*60}")
    
    # Convert geographic coordinates to rotated for interpolation
    transformer = CoordinateTransformer.from_dataset(ds)
    
    # Interpolate at mesh points
    print(f"\n  Interpolating at {len(mesh)} mesh points...")
    mesh_rlat, mesh_rlon = transformer.geographic_to_rotated(
        mesh['lat'].values,
        mesh['lon'].values
    )
    
    mesh = mesh.copy()
    mesh['rlat'] = mesh_rlat
    mesh['rlon'] = mesh_rlon
    
    try:
        mesh['value_rbf'] = interp.interpolate(mesh_rlat, mesh_rlon, method='rbf')
        mesh['value_linear'] = interp.interpolate(mesh_rlat, mesh_rlon, method='linear')
        print(f"✓ Mesh interpolation complete")
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
        print(f"⚠ Warning: Mesh interpolation failed: {e}")
        mesh['value_rbf'] = np.nan
        mesh['value_linear'] = np.nan
    
    # Interpolate at station points
    print(f"\n  Interpolating at {len(stations)} station points...")
    station_rlat, station_rlon = transformer.geographic_to_rotated(
        stations['lat'].values,
        stations['lon'].values
    )
    
    stations = stations.copy()
    stations['rlat'] = station_rlat
    stations['rlon'] = station_rlon
    
    try:
        stations['value_rbf'] = interp.interpolate(station_rlat, station_rlon, method='rbf')
        stations['value_linear'] = interp.interpolate(station_rlat, station_rlon, method='linear')
        print(f"✓ Station interpolation complete")
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
        print(f"⚠ Warning: Station interpolation failed: {e}")
        stations['value_rbf'] = np.nan
        stations['value_linear'] = np.nan
    
    return mesh, stations


def evaluate_interpolation_quality(interp, grid_points):
    """
    Evaluate interpolation quality using cross-validation.
    
    Args:
        interp: RemoInterpolator instance
        grid_points: Grid points DataFrame
    
    Returns:
        Dictionary with quality metrics
    """
    print(f"\n{'='*60}")
    print("STEP 5: Evaluating Interpolation Quality")
    print(f"{'='*60}")
    
    # Use a subset of grid points for testing
    n_test = min(50, len(grid_points))
    test_indices = np.random.choice(len(grid_points), n_test, replace=False)
    test_points = grid_points.iloc[test_indices]
    
    # Get ground truth values
    true_values = []
    for _, point in test_points.iterrows():
        try:
            val = float(interp.dataset[interp.variable].isel(
                time=interp.time_idx,
                rlat=int(point['rlat_idx']),
                rlon=int(point['rlon_idx'])
            ).values)
            true_values.append(val)
        except (IndexError, KeyError, ValueError) as e:
            true_values.append(np.nan)
    
    true_values = np.array(true_values)
    
    # Interpolate at test points
    test_coords = np.column_stack([test_points['rlat'].values, test_points['rlon'].values])
    
    # Remove points with NaN true values
    valid_mask = ~np.isnan(true_values)
    test_coords = test_coords[valid_mask]
    true_values = true_values[valid_mask]
    
    if len(true_values) < 5:
        print("⚠ Warning: Not enough valid test points for quality evaluation")
        return {}
    
    # Calculate errors for different methods
    results = {}
    for method in ['rbf', 'linear']:
        try:
            predicted = interp.interpolate(
                test_coords[:, 0],
                test_coords[:, 1],
                method=method
            )
            
            errors = calculate_interpolation_error(
                interp,
                test_coords,
                true_values,
                method=method
            )
            
            results[method] = errors
            
            print(f"\n  Method: {method}")
            print(f"    MAE:  {errors['mae']:.4f}")
            print(f"    RMSE: {errors['rmse']:.4f}")
            print(f"    R²:   {errors['r2']:.4f}")
            
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
            print(f"  ⚠ Error evaluating {method}: {e}")
    
    print(f"\n✓ Quality evaluation complete")
    return results


def create_visualization(ds, mesh, stations, grid_points, interp, quality_metrics):
    """
    Create interactive HTML visualization.
    
    Args:
        ds: REMO dataset
        mesh: Mesh with interpolated values
        stations: Stations with interpolated values
        grid_points: Original grid points
        interp: RemoInterpolator instance
        quality_metrics: Quality evaluation results
    """
    print(f"\n{'='*60}")
    print("STEP 6: Creating Visualization")
    print(f"{'='*60}")
    
    # Get domain center
    domain = GermanyDomain()
    center_lat, center_lon = domain.get_center()
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add domain boundary
    bounds = [[domain.lat_min, domain.lon_min], [domain.lat_max, domain.lon_max]]
    folium.Rectangle(
        bounds=bounds,
        color='red',
        fill=False,
        weight=2,
        popup='Germany Domain'
    ).add_to(m)
    
    # Add original grid points (large blue circles)
    grid_feature_group = folium.FeatureGroup(name='REMO Grid Points')
    for idx, point in grid_points.iterrows():
        if idx % 10 == 0:  # Subsample for visibility
            folium.CircleMarker(
                location=[point['lat'], point['lon']],
                radius=6,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.6,
                popup=f"Grid Point<br>Lat: {point['lat']:.2f}<br>Lon: {point['lon']:.2f}"
            ).add_to(grid_feature_group)
    grid_feature_group.add_to(m)
    
    # Add weather stations (red markers)
    station_feature_group = folium.FeatureGroup(name='Weather Stations')
    for idx, station in stations.iterrows():
        value_text = ""
        if 'value_rbf' in station and not np.isnan(station['value_rbf']):
            value = station['value_rbf']
            if interp.variable == 'TS':
                value_c = kelvin_to_celsius(value)
                value_text = f"<br>Temp (RBF): {value_c:.1f}°C"
            else:
                value_text = f"<br>Value (RBF): {value:.2f}"
        
        folium.Marker(
            location=[station['lat'], station['lon']],
            icon=folium.Icon(color='red', icon='info-sign'),
            popup=f"<b>{station['name']}</b><br>Lat: {station['lat']:.2f}<br>Lon: {station['lon']:.2f}{value_text}"
        ).add_to(station_feature_group)
    station_feature_group.add_to(m)
    
    # Add interpolated mesh points (small green circles with color scale)
    mesh_feature_group = folium.FeatureGroup(name='Interpolated Mesh')
    
    # Get value range for color scaling
    if 'value_rbf' in mesh.columns:
        valid_values = mesh['value_rbf'].dropna()
        if len(valid_values) > 0:
            vmin, vmax = valid_values.min(), valid_values.max()
            
            # Subsample mesh for display
            mesh_sample = mesh.sample(n=min(500, len(mesh)))
            
            for idx, point in mesh_sample.iterrows():
                if not np.isnan(point['value_rbf']):
                    # Normalize value for color
                    norm_val = (point['value_rbf'] - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                    
                    # Color from blue (cold) to red (hot)
                    r = int(255 * norm_val)
                    b = int(255 * (1 - norm_val))
                    color = f'#{r:02x}88{b:02x}'
                    
                    # Format value for display
                    if interp.variable == 'TS':
                        value_display = f"{kelvin_to_celsius(point['value_rbf']):.2f}°C"
                    else:
                        value_display = f"{point['value_rbf']:.2f}"
                    
                    folium.CircleMarker(
                        location=[point['lat'], point['lon']],
                        radius=3,
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.6,
                        popup=f"Interpolated<br>Value: {value_display}"
                    ).add_to(mesh_feature_group)
    
    mesh_feature_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add title
    title_html = '''
    <div style="position: fixed; 
                top: 10px; left: 50px; width: 400px; height: 90px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>REMO Climate Data Interpolation Demo</h4>
    <p><b style="color:blue">Blue</b>: Original REMO grid points<br>
       <b style="color:red">Red</b>: Weather stations<br>
       <b style="color:green">Green</b>: Interpolated mesh</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save map
    output_file = 'interpolation_demo_map.html'
    m.save(output_file)
    print(f"✓ Interactive map saved to '{output_file}'")
    
    # Save results to CSV
    mesh_out = mesh[['lat', 'lon', 'value_rbf', 'value_linear']].copy()
    
    # Add Celsius columns if variable is TS
    if interp.variable == 'TS':
        mesh_out['value_rbf_celsius'] = kelvin_to_celsius(mesh_out['value_rbf'])
        mesh_out['value_linear_celsius'] = kelvin_to_celsius(mesh_out['value_linear'])
    
    mesh_out.to_csv('interpolation_results.csv', index=False)
    print(f"✓ Results saved to 'interpolation_results.csv'")
    
    # Create quality report
    create_quality_report(interp, quality_metrics, mesh, stations, grid_points)


def create_quality_report(interp, quality_metrics, mesh, stations, grid_points):
    """
    Create text report on interpolation quality.
    
    Args:
        interp: RemoInterpolator instance
        quality_metrics: Quality evaluation results
        mesh: Mesh DataFrame
        stations: Stations DataFrame
        grid_points: Grid points DataFrame
    """
    stats = interp.get_statistics()
    
    # Check if variable is temperature to format values appropriately
    is_temperature = interp.variable == 'TS'
    
    # Format value range and mean based on variable type
    if is_temperature:
        value_min = kelvin_to_celsius(stats['value_min'])
        value_max = kelvin_to_celsius(stats['value_max'])
        value_mean = kelvin_to_celsius(stats['value_mean'])
        value_unit = "°C"
    else:
        value_min = stats['value_min']
        value_max = stats['value_max']
        value_mean = stats['value_mean']
        value_unit = ""
    
    report = f"""
{'='*60}
REMO POLYNOMIAL INTERPOLATION - QUALITY REPORT
{'='*60}

INTERPOLATION SETUP:
  Variable: {interp.variable}
  Time index: {interp.time_idx}
  Kernel: {interp.kernel}
  Neighbors: {interp.neighbors}
  
GRID STATISTICS:
  Total grid points: {stats['total_points']}
  Valid points: {stats['valid_points']}
  Missing points: {stats['nan_points']}
  Value range: {value_min:.2f}{value_unit} to {value_max:.2f}{value_unit}
  Mean value: {value_mean:.2f}{value_unit}
  
INTERPOLATION COVERAGE:
  Mesh points: {len(mesh)}
  Weather stations: {len(stations)}
  Original grid points: {len(grid_points)}
  
QUALITY METRICS (Cross-validation):
"""
    
    for method, metrics in quality_metrics.items():
        # Convert error metrics to Celsius if temperature variable
        if is_temperature:
            mae = kelvin_to_celsius(metrics['mae'] + 273.15) - kelvin_to_celsius(273.15)  # Convert delta
            rmse = kelvin_to_celsius(metrics['rmse'] + 273.15) - kelvin_to_celsius(273.15)  # Convert delta
            mean_error = kelvin_to_celsius(metrics['mean_error'] + 273.15) - kelvin_to_celsius(273.15)
            std_error = kelvin_to_celsius(metrics['std_error'] + 273.15) - kelvin_to_celsius(273.15)
            error_unit = "°C"
        else:
            mae = metrics['mae']
            rmse = metrics['rmse']
            mean_error = metrics['mean_error']
            std_error = metrics['std_error']
            error_unit = ""
        
        report += f"""
  Method: {method.upper()}
    Mean Absolute Error (MAE): {mae:.4f}{error_unit}
    Root Mean Square Error (RMSE): {rmse:.4f}{error_unit}
    R² Score: {metrics['r2']:.4f}
    Mean Error: {mean_error:.4f}{error_unit}
    Std Error: {std_error:.4f}{error_unit}
    Test points: {metrics['n_points']}
"""
    
    report += f"""
OUTPUT FILES:
  - interpolation_demo_map.html: Interactive visualization
  - interpolation_results.csv: Interpolated values at mesh points
  - interpolation_quality_report.txt: This report

INTERPRETATION:
  Lower MAE/RMSE values indicate better interpolation accuracy.
  R² closer to 1.0 indicates better fit to original data.
  RBF (thin-plate spline) typically provides smoother surfaces than linear.
  
{'='*60}
"""
    
    with open('interpolation_quality_report.txt', 'w') as f:
        f.write(report)
    
    print(report)
    print(f"✓ Quality report saved to 'interpolation_quality_report.txt'")


def main():
    """Main demonstration workflow."""
    print("="*60)
    print("REMO POLYNOMIAL INTERPOLATION DEMO")
    print("="*60)
    print("\nThis demo shows polynomial interpolation for downscaling")
    print("REMO climate model data from coarse grids to fine resolution.")
    
    # Load data
    ds = load_demo_data()
    
    # Set up interpolation for temperature (TS = surface temperature)
    variable = 'TS'
    interp = setup_interpolation(ds, variable=variable)
    
    # Generate mesh and stations
    mesh, stations, grid_points = generate_mesh_and_stations(ds)
    
    # Perform interpolation
    mesh, stations = perform_interpolation(interp, mesh, stations, grid_points, ds)
    
    # Evaluate quality
    quality_metrics = evaluate_interpolation_quality(interp, grid_points)
    
    # Create visualization
    create_visualization(ds, mesh, stations, grid_points, interp, quality_metrics)
    
    print(f"\n{'='*60}")
    print("✓ DEMO COMPLETE!")
    print(f"{'='*60}")
    print("\nGenerated files:")
    print("  1. interpolation_demo_map.html - Open in browser to view results")
    print("  2. interpolation_results.csv - Interpolated values")
    print("  3. interpolation_quality_report.txt - Quality metrics")
    print("\nThe map shows:")
    print("  - Blue circles: Original REMO grid points (coarse)")
    print("  - Red markers: Weather station locations")
    print("  - Green circles: Interpolated mesh (fine resolution)")
    print("="*60)


if __name__ == '__main__':
    main()
