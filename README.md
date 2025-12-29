# Klimawerke - REMO Climate Model Data Processing

This repository provides tools for downloading, processing, and analyzing REMO regional climate model data with a focus on downscaling from coarse grids to fine resolution using polynomial interpolation.

## Features

### 1. Data Download and Exploration
- Download REMO demo data from GitHub repositories
- Explore NetCDF file structure and metadata
- Extract regional subsets (e.g., Germany)
- Basic visualization with folium maps

### 2. Polynomial Interpolation Module ⭐ NEW
Comprehensive toolkit for downscaling REMO climate data from coarse grids (EUR-44, EUR-22, EUR-11) to regional and point-level resolution.

#### Key Capabilities:
- **2D Polynomial Interpolation**: Uses Radial Basis Functions (RBF) with thin-plate spline kernel for smooth surfaces
- **Multiple Interpolation Methods**: RBF, linear, and cubic interpolation
- **Rotated Coordinate Support**: Native handling of REMO's rotated pole coordinate system
- **Mesh Generation**: Create regular grids over arbitrary geographic regions
- **Weather Station Integration**: Support for validation with weather station data
- **Missing Value Handling**: Graceful handling of NaN values in climate data
- **Quality Metrics**: Cross-validation and error analysis (MAE, RMSE, R²)

## Installation

```bash
# Clone the repository
git clone https://github.com/LarsBoettger70/Klimawerke.git
cd Klimawerke

# Install dependencies
pip install -r requirements.txt
```

### Requirements
- Python 3.7+
- xarray
- netCDF4
- scipy
- numpy
- pandas
- geopandas
- folium
- matplotlib
- shapely

## Quick Start

### 1. Download Demo Data
```bash
python3 download_and_explore_demodata.py
```

This downloads a small REMO EUR-44 demo file (~16 MB) and extracts a Germany subset.

### 2. Run Interpolation Demo
```bash
python3 interpolation_demo.py
```

This demonstrates the complete interpolation workflow:
- Loads REMO demo data
- Generates a mesh over Germany (0.5° resolution)
- Creates synthetic and real weather station points
- Performs polynomial interpolation
- Creates interactive HTML visualization
- Generates quality report

### Output Files:
- `interpolation_demo_map.html` - Interactive map showing grid points, stations, and interpolated surface
- `interpolation_results.csv` - Interpolated values at mesh points (includes both Kelvin and Celsius values for temperature variables)
- `interpolation_quality_report.txt` - Quality metrics and statistics (temperature metrics shown in Celsius)

## Usage Examples

### Basic Interpolation

```python
import xarray as xr
from polynomial_interpolation import RemoInterpolator, kelvin_to_celsius

# Load REMO data
ds = xr.open_dataset('remo_germany_subset.nc')

# Create interpolator for surface temperature
interp = RemoInterpolator(
    ds, 
    variable='TS',
    time_idx=0,
    kernel='thin_plate_spline',
    neighbors=16
)

# Interpolate at specific points (rotated coordinates)
values = interp.interpolate(
    query_rlat=[0.5, 1.0, 1.5],
    query_rlon=[5.0, 5.5, 6.0],
    method='rbf'
)

# Convert temperature from Kelvin to Celsius
values_celsius = kelvin_to_celsius(values)
print(f"Temperatures: {values_celsius}°C")

# Interpolate over a regular grid
rlat_grid, rlon_grid, values_grid = interp.interpolate_grid(
    rlat_range=(-5, 5),
    rlon_range=(-10, 10),
    resolution=0.1,
    method='rbf'
)
```

### Mesh Generation

```python
from mesh_generator import MeshGenerator, GermanyDomain

# Generate mesh over Germany
domain = GermanyDomain()
mesh_gen = MeshGenerator(domain)
mesh = mesh_gen.generate_mesh(resolution=0.1)  # 0.1° resolution

print(f"Generated {len(mesh)} mesh points")
# Output: lat, lon, point_id columns
```

### Weather Station Management

```python
from mesh_generator import WeatherStationManager, GermanyDomain

# Create station manager
station_mgr = WeatherStationManager()

# Add real German weather stations
stations = station_mgr.get_german_reference_stations()

# Generate synthetic stations for testing
domain = GermanyDomain()
synthetic = station_mgr.generate_synthetic_stations(
    domain, 
    n_stations=20, 
    seed=42
)

# Get all stations
all_stations = station_mgr.to_dataframe()
```

### Coordinate Transformation

```python
from mesh_generator import CoordinateTransformer
import xarray as xr

# Load dataset and create transformer
ds = xr.open_dataset('remo_EUR-44.nc')
transformer = CoordinateTransformer.from_dataset(ds)

# Convert geographic to rotated coordinates
rlat, rlon = transformer.geographic_to_rotated(
    lat=[51.0, 52.0],
    lon=[10.0, 11.0]
)

# Convert back to geographic
lat, lon = transformer.rotated_to_geographic(rlat, rlon)
```

## Module Documentation

### polynomial_interpolation.py

**Main Class: `RemoInterpolator`**

Creates smooth polynomial surfaces through REMO grid points for downscaling.

**Key Methods:**
- `interpolate(query_rlat, query_rlon, method='rbf')` - Interpolate at arbitrary points
- `interpolate_grid(rlat_range, rlon_range, resolution, method='rbf')` - Interpolate over regular grid
- `find_neighbors(query_rlat, query_rlon, k=None)` - Find k nearest grid points
- `get_statistics()` - Get grid statistics

**Utility Functions:**
- `kelvin_to_celsius(kelvin_value)` - Convert temperature from Kelvin to Celsius
- `calculate_interpolation_error(interpolator, test_points, true_values, method)` - Calculate error metrics

**Interpolation Methods:**
- `rbf`: Radial Basis Function with thin-plate spline (smooth, recommended)
- `linear`: Linear interpolation (fast, less smooth)
- `cubic`: Cubic interpolation (balanced)

### mesh_generator.py

**Classes:**
- `Domain` - Geographic domain definition
- `GermanyDomain` - Pre-defined Germany bounds
- `MeshGenerator` - Generate regular meshes
- `CoordinateTransformer` - Convert between coordinate systems
- `WeatherStationManager` - Manage weather station data

**Key Functions:**
- `extract_remo_grid_in_domain(dataset, domain)` - Extract grid points within domain

### interpolation_demo.py

Complete demonstration script showing:
1. Data loading
2. Interpolator setup
3. Mesh and station generation
4. Interpolation execution
5. Quality evaluation
6. Visualization creation

## Mathematical Approach

### Radial Basis Function Interpolation

The module uses RBF interpolation with a thin-plate spline kernel, which provides smooth C² continuous surfaces. For each query point:

1. Find k nearest neighbors in the REMO grid (default: k=16)
2. Fit a local RBF interpolator through these neighbors
3. Evaluate the interpolator at the query point

The thin-plate spline kernel minimizes bending energy, creating natural-looking smooth transitions between grid points, avoiding the blocky appearance of nearest-neighbor or linear interpolation.

### Why Polynomial/RBF for Climate Data?

- **Smooth transitions**: Climate variables change gradually in space
- **No artificial discontinuities**: Unlike nearest-neighbor
- **Handles irregular grids**: Works with rotated pole coordinates
- **Local support**: Uses nearby points, adapts to local patterns
- **Mathematically sound**: Minimizes curvature for natural surfaces

## Coordinate Systems

REMO uses a rotated pole coordinate system:
- **Rotated coordinates**: (rlat, rlon) - model grid coordinates
- **Geographic coordinates**: (lat, lon) - standard WGS84

The module handles both systems:
- Interpolation works in rotated coordinates
- Visualization uses geographic coordinates
- Automatic conversion via `CoordinateTransformer`

## Quality Metrics

The interpolation quality is evaluated using:
- **MAE** (Mean Absolute Error): Average absolute difference
- **RMSE** (Root Mean Square Error): Standard deviation of errors
- **R²** (Coefficient of Determination): Proportion of variance explained

Cross-validation: Interpolate at known grid points and compare with actual values.

## Data Sources

### REMO Demo Data
- EUR-44: ~50 km resolution, full Europe domain
- EUR-22: ~25 km resolution (downloadable separately)
- EUR-11: ~12.5 km resolution (downloadable separately)

Demo data from: https://github.com/remo-rcm/pyremo-data

### Domain Information
REMO domains from: https://github.com/remo-rcm/tables

## File Structure

```
Klimawerke/
├── polynomial_interpolation.py   # Core interpolation engine
├── mesh_generator.py             # Mesh and coordinate tools
├── interpolation_demo.py         # Complete demo workflow
├── download_and_explore_demodata.py  # Data download
├── load_remo_domains.py          # Domain definitions
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── *.nc                         # NetCDF data files (not in git)
```

## Visualization

The demo generates an interactive Folium map with three layers:
1. **Blue circles**: Original REMO grid points (coarse)
2. **Red markers**: Weather station locations
3. **Green circles**: Interpolated mesh points (fine resolution)

Click on any point to see values. Toggle layers on/off.

## Performance Notes

- **Grid size**: 100x100 grid → 10,000 points processes in ~5 seconds
- **Interpolation**: 396 mesh points with RBF → ~2 seconds
- **Memory**: ~100 MB for Germany subset
- **Scaling**: Linear with number of query points, logarithmic with grid size (KD-tree)

## Limitations and Future Work

### Current Limitations:
- Coordinate transformation uses simplified formulas (good for small regions)
- Single time step support (temporal interpolation not yet implemented)
- No elevation correction (important for temperature)
- Memory-intensive for very large domains

### Planned Enhancements:
- [ ] Temporal interpolation
- [ ] Multi-variable interpolation
- [ ] Elevation-aware downscaling
- [ ] Parallel processing for large domains
- [ ] Integration with other climate models
- [ ] Real weather station data integration
- [ ] Uncertainty quantification

## Contributing

Contributions welcome! Areas for improvement:
- More accurate coordinate transformations (using pyproj/cartopy)
- Additional interpolation methods
- Performance optimizations
- Real weather station data connectors
- Validation against observations

## References

- REMO Model: https://remo-rcm.de/
- CORDEX: https://cordex.org/
- Radial Basis Functions: Buhmann, M. D. (2003). Radial Basis Functions: Theory and Implementations

## License

This project is open source. See repository for license details.

## Authors

- LarsBoettger70 (Repository Owner)
- Contributors welcome

## Citation

If you use this code in research, please cite:
```
Klimawerke REMO Interpolation Tools (2024)
GitHub: https://github.com/LarsBoettger70/Klimawerke
```

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact repository owner

---

Last updated: December 2024
