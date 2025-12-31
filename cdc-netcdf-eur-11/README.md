# CDC European Weather and Wave Data Visualization

This directory contains scripts to visualize CDC (Climate Data Centre) European weather and wave data using interactive maps with time slider functionality.

## Overview

The solution processes NetCDF files containing weather and wave data, interpolates them to a common grid, generates GeoJSON files, and creates an interactive Folium map with layer controls.

## Data Files

The following NetCDF files are required:
- `data_stream-wave_stepType-instant.nc` - Wave data (17x21 grid, 576 time steps)
  - Variables: swh (significant wave height), mwd (mean wave direction), mwp (mean wave period)
- `data_stream-oper_stepType-instant.nc` - Weather instant data (33x41 grid, 576 time steps)
  - Variables: t2m, u10, v10, d2m, msl, sst, sp
- `data_stream-oper_stepType-accum.nc` - Weather accumulated data (33x41 grid, 576 time steps)
  - Variables: tp (total precipitation)

## Scripts

### 1. A3_1_generate_geojson_from_netcdf.py

**Purpose**: Generates GeoJSON files from NetCDF data

**Features**:
- Loads all three NetCDF files
- Interpolates wave data from 17x21 to 33x41 grid using scipy griddata
- Calculates wind speed from u10 and v10 components
- Converts temperatures from Kelvin to Celsius
- Converts precipitation to mm
- Generates separate GeoJSON files for each variable and time step
- Creates a timeseries index JSON file for the time slider
- Processes 24 time steps (daily snapshots) to optimize performance

**Usage**:
```bash
cd cdc-netcdf-eur-11
python3 A3_1_generate_geojson_from_netcdf.py
```

**Output**:
- Directory: `geojson/`
- Files: 120 GeoJSON files (5 variables × 24 time steps)
- Index: `geojson/timeseries_index.json`

### 2. A3_2_build_interactive_map_with_timeslider.py

**Purpose**: Creates an interactive HTML map with layer controls

**Features**:
- Loads pre-generated GeoJSON files
- Creates circle markers with size and color based on data values
- Implements layer control for toggling variables:
  - Significant Wave Height (swh)
  - Temperature 2m (t2m)
  - Total Precipitation (tp)
  - Wind Speed (calculated)
  - Sea Surface Temperature (sst)
- Interactive tooltips with detailed information
- Multiple base map options (OpenStreetMap, Light, Dark)
- Fullscreen mode
- Distance measurement tool
- Minimap for navigation

**Usage**:
```bash
cd cdc-netcdf-eur-11
python3 A3_2_build_interactive_map_with_timeslider.py
```

**Output**:
- File: `interactive_map_with_timeslider.html`
- Size: ~5.2MB
- Open in any web browser

## Workflow

1. **Generate GeoJSON files**:
   ```bash
   python3 A3_1_generate_geojson_from_netcdf.py
   ```
   This takes ~2-3 minutes and creates the `geojson/` directory with all data files.

2. **Build interactive map**:
   ```bash
   python3 A3_2_build_interactive_map_with_timeslider.py
   ```
   This takes ~1 minute and creates `interactive_map_with_timeslider.html`.

3. **View the map**:
   Open `interactive_map_with_timeslider.html` in your web browser.

## Data Processing Details

### Grid Interpolation
Wave data is interpolated from the coarser 17x21 grid to the finer 33x41 weather grid using scipy's `griddata` function with linear interpolation. This ensures all variables are on the same spatial grid for consistent visualization.

### Value Transformations
- **Temperature**: Converted from Kelvin to Celsius (subtract 273.15)
- **Precipitation**: Converted to millimeters (multiply by 1000)
- **Wind Speed**: Calculated as √(u10² + v10²)
- **NaN Values**: Properly handled and excluded from visualization

### Color Scales
Each variable has a custom color scale optimized for its value range:
- **Wave Height**: 0-4m (blue to red)
- **Temperature**: -5 to 25°C (blue to red)
- **Precipitation**: 0-0.5mm (light to dark blue)
- **Wind Speed**: 0-20 m/s (yellow to brown)
- **SST**: 5-20°C (blue to red)

## Performance Optimization

To avoid browser performance issues with large datasets:
- Only 24 time steps are processed (daily snapshots instead of hourly)
- NaN values are filtered out before creating markers
- Circle markers are used instead of polygons for better performance
- The first time step is loaded initially, with others available through the layer control

## Dependencies

Required Python packages:
- xarray
- numpy
- scipy
- folium
- pandas
- json (standard library)
- os (standard library)

Install with:
```bash
pip install xarray numpy scipy folium pandas
```

## Troubleshooting

**Issue**: "NetCDF file not found"
- **Solution**: Ensure all three NetCDF files are in the `cdc-netcdf-eur-11/` directory

**Issue**: Map loads slowly in browser
- **Solution**: This is expected due to the large number of features. Consider reducing the time step interval in the generator script.

**Issue**: Some markers are missing
- **Solution**: This is expected for NaN values in the data. The North Sea area has valid wave data while inland areas show temperature and precipitation.

## File Structure

```
cdc-netcdf-eur-11/
├── A3_1_generate_geojson_from_netcdf.py
├── A3_2_build_interactive_map_with_timeslider.py
├── README.md
├── data_stream-wave_stepType-instant.nc
├── data_stream-oper_stepType-instant.nc
├── data_stream-oper_stepType-accum.nc
├── geojson/
│   ├── timeseries_index.json
│   ├── swh_*.geojson (24 files)
│   ├── t2m_*.geojson (24 files)
│   ├── tp_*.geojson (24 files)
│   ├── wind_speed_*.geojson (24 files)
│   └── sst_*.geojson (24 files)
└── interactive_map_with_timeslider.html
```

## Next Steps

To enhance this solution:
1. Implement true time slider functionality using Folium's TimeSlider plugin
2. Add animation controls to automatically cycle through time steps
3. Create summary statistics panels showing min/max/mean values
4. Add ability to download data for specific locations
5. Implement spatial analysis tools (e.g., regional averages)
6. Add comparison views to show multiple variables side-by-side

## License

This solution uses open data from the Climate Data Centre (CDC).
