'''
Interactive Map Builder with Date Picker (Phase 1)
Loads pre-generated GeoJSON files and creates an interactive Folium map
with layer control and interactive date picker functionality
'''

import folium
from folium import plugins
import json
import os
import numpy as np
from datetime import datetime

# Configuration
GEOJSON_DIR = 'geojson'
OUTPUT_FILE = 'interactive_map_with_datepicker.html'

# Date Picker Configuration
DEFAULT_DATE_MODE = 'today'  # Options: 'today', 'first', or ISO date string (e.g., '2024-01-15')
ENABLE_DATE_PICKER = True

# List of variables to process
VARIABLES = ['swh', 't2m', 'tp', 'wind_speed', 'sst']

# Color scales for different variables
COLOR_SCALES = {
    'swh': {
        'name': 'Significant Wave Height (m)',
        'colors': ['#3288bd', '#66c2a5', '#abdda4', '#e6f598', '#fee08b', '#fdae61', '#f46d43', '#d53e4f'],
        'vmin': 0,
        'vmax': 4
    },
    't2m': {
        'name': 'Temperature 2m (°C)',
        'colors': ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027'],
        'vmin': -5,
        'vmax': 25
    },
    'tp': {
        'name': 'Total Precipitation (mm)',
        'colors': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
        'vmin': 0,
        'vmax': 0.5
    },
    'wind_speed': {
        'name': 'Wind Speed (m/s)',
        'colors': ['#ffffe5', '#fff7bc', '#fee391', '#fec44f', '#fe9929', '#ec7014', '#cc4c02', '#993404', '#662506'],
        'vmin': 0,
        'vmax': 20
    },
    'sst': {
        'name': 'Sea Surface Temperature (°C)',
        'colors': ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027'],
        'vmin': 5,
        'vmax': 20
    }
}


def value_to_color(value, colors, vmin, vmax):
    '''Convert a value to a color based on color scale'''
    if np.isnan(value):
        return '#808080'  # Gray for NaN
    
    # Normalize value to 0-1
    normalized = (value - vmin) / (vmax - vmin)
    normalized = max(0, min(1, normalized))  # Clamp to 0-1
    
    # Get color index
    idx = int(normalized * (len(colors) - 1))
    return colors[idx]


def value_to_radius(value, vmin, vmax, min_radius=2, max_radius=10):
    '''Convert a value to a circle radius'''
    if np.isnan(value):
        return min_radius
    
    # Normalize value to 0-1
    normalized = (value - vmin) / (vmax - vmin)
    normalized = max(0, min(1, normalized))  # Clamp to 0-1
    
    # Linear interpolation
    return min_radius + normalized * (max_radius - min_radius)


def extract_date_from_timestamp(timestamp):
    '''Extract YYYY-MM-DD from ISO timestamp string'''
    # Timestamp format: "2024-01-15T00:00:00"
    return timestamp.split('T')[0]


def get_default_date(index, default_mode):
    '''
    Determine which date to load based on configuration
    
    Args:
        index: The timeseries index dictionary
        default_mode: 'today', 'first', or ISO date string
    
    Returns:
        ISO date string (YYYY-MM-DD)
    '''
    if not index or not index.get('timestamps'):
        return None
    
    available_dates = [extract_date_from_timestamp(ts) for ts in index['timestamps']]
    
    if default_mode == 'first':
        return available_dates[0]
    elif default_mode == 'today':
        today = datetime.now().strftime('%Y-%m-%d')
        return find_nearest_date(today, available_dates)
    else:
        # Assume it's an ISO date string
        return find_nearest_date(default_mode, available_dates)


def find_nearest_date(target_date, available_dates):
    '''
    Find the nearest available date to the target date
    
    Args:
        target_date: Target date string (YYYY-MM-DD)
        available_dates: List of available date strings
    
    Returns:
        Nearest date string from available_dates
    '''
    if not available_dates:
        return None
    
    try:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        # Invalid date format, return first date
        return available_dates[0]
    
    # Convert all dates to datetime objects
    date_objects = []
    for date_str in available_dates:
        try:
            date_objects.append(datetime.strptime(date_str, '%Y-%m-%d'))
        except ValueError:
            continue
    
    if not date_objects:
        return available_dates[0]
    
    # Find closest date
    closest = min(date_objects, key=lambda d: abs((d - target_dt).total_seconds()))
    return closest.strftime('%Y-%m-%d')


def get_timestamp_for_date(date_str, index):
    '''
    Get the full ISO timestamp for a given date
    
    Args:
        date_str: Date string (YYYY-MM-DD)
        index: The timeseries index dictionary
    
    Returns:
        Full ISO timestamp string or None
    '''
    for timestamp in index['timestamps']:
        if extract_date_from_timestamp(timestamp) == date_str:
            return timestamp
    return None


def get_geojson_files_for_timestamp(timestamp, index, var_name):
    '''
    Get the GeoJSON filename for a specific variable and timestamp
    
    Args:
        timestamp: ISO timestamp string
        index: The timeseries index dictionary
        var_name: Variable name (e.g., 'swh', 't2m')
    
    Returns:
        GeoJSON filename or None
    '''
    if var_name not in index['files']:
        return None
    
    # Find the index of the timestamp
    try:
        timestamp_idx = index['timestamps'].index(timestamp)
        return index['files'][var_name][timestamp_idx]
    except (ValueError, IndexError):
        return None


def load_timeseries_index():
    '''Load the timeseries index file'''
    index_file = os.path.join(GEOJSON_DIR, 'timeseries_index.json')
    
    if not os.path.exists(index_file):
        print(f'✗ Error: {index_file} not found')
        print('Please run A3_1_generate_geojson_from_netcdf.py first')
        return None
    
    with open(index_file, 'r') as f:
        index = json.load(f)
    
    print(f'✓ Loaded timeseries index with {len(index["timestamps"])} time steps')
    return index


def create_layer_for_variable(m, var_name, geojson_files, timestamps):
    '''
    Create a FeatureGroup layer for a specific variable with time slider support
    '''
    print(f'\nCreating layer for {var_name}...')
    
    config = COLOR_SCALES[var_name]
    feature_group = folium.FeatureGroup(name=config['name'], show=True)
    
    # Create timestamped GeoJSON layers
    time_indexed_geojsons = []
    
    for idx, (geojson_file, timestamp) in enumerate(zip(geojson_files, timestamps)):
        geojson_path = os.path.join(GEOJSON_DIR, geojson_file)
        
        if not os.path.exists(geojson_path):
            print(f'  ✗ Warning: {geojson_path} not found')
            continue
        
        # Load GeoJSON
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Create features for this timestamp
        features = []
        for feature in geojson_data['features']:
            value = feature['properties']['value']
            lat = feature['geometry']['coordinates'][1]
            lon = feature['geometry']['coordinates'][0]
            
            # Create a circle marker
            color = value_to_color(value, config['colors'], config['vmin'], config['vmax'])
            radius = value_to_radius(value, config['vmin'], config['vmax'])
            
            # Create marker with popup
            popup_text = f"""
            <b>{config['name']}</b><br>
            Value: {value:.2f}<br>
            Lat: {lat:.2f}°<br>
            Lon: {lon:.2f}°<br>
            Time: {timestamp}
            """
            
            marker = folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1,
                popup=folium.Popup(popup_text, max_width=250)
            )
            
            features.append(marker)
        
        # Store for time series
        time_indexed_geojsons.append({
            'timestamp': timestamp,
            'features': features
        })
        
        print(f'  Processed {idx + 1}/{len(geojson_files)}: {geojson_file} ({len(features)} features)')
    
    # Add only the first timestamp to the map initially
    if time_indexed_geojsons:
        for feature in time_indexed_geojsons[0]['features']:
            feature.add_to(feature_group)
    
    feature_group.add_to(m)
    
    print(f'✓ Created layer for {var_name}')
    return feature_group, time_indexed_geojsons


def create_interactive_map(index):
    '''
    Create the main interactive map with all layers and controls
    '''
    print('\nCreating interactive map...')
    
    # Determine default date to load
    default_date = get_default_date(index, DEFAULT_DATE_MODE)
    default_timestamp = get_timestamp_for_date(default_date, index) if default_date else index['timestamps'][0]
    
    print(f'Default date: {default_date}')
    print(f'Default timestamp: {default_timestamp}')
    
    # Extract available dates for the date picker
    available_dates = [extract_date_from_timestamp(ts) for ts in index['timestamps']]
    min_date = min(available_dates)
    max_date = max(available_dates)
    
    print(f'Date range: {min_date} to {max_date}')
    
    # Calculate center of map (middle of Europe region)
    center_lat = 51.0  # Middle of lat range 47-55
    center_lon = 10.0  # Middle of lon range 5-15
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add alternative tile layers
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    
    # Create layers for each variable
    layers = {}
    time_data = {}
    
    for var_name in VARIABLES:
        if var_name in index['files']:
            geojson_files = index['files'][var_name]
            timestamps = index['timestamps']
            
            layer, time_indexed_data = create_layer_for_variable(
                m, var_name, geojson_files, timestamps
            )
            layers[var_name] = layer
            time_data[var_name] = time_indexed_data
    
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Add custom legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; 
                background-color: white; border:2px solid grey; 
                z-index:9999; font-size:14px;
                padding: 10px;
                border-radius: 5px;">
    <p style="margin: 0; font-weight: bold;">Legend</p>
    <p style="margin: 5px 0; font-size: 12px;">
        <span style="color: #d53e4f;">●</span> High values<br>
        <span style="color: #fee08b;">●</span> Medium values<br>
        <span style="color: #3288bd;">●</span> Low values
    </p>
    <p style="margin: 5px 0; font-size: 11px; color: #666;">
        Circle size indicates magnitude
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add date picker UI (if enabled)
    if ENABLE_DATE_PICKER:
        datepicker_html = f'''
        <div id="date-picker-container" style="position: fixed; 
                    top: 10px; left: 50%; transform: translateX(-50%);
                    background-color: white; border: 2px solid #333; 
                    z-index: 9999; 
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                    font-family: Arial, sans-serif;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <label for="date-input" style="font-weight: bold; font-size: 14px;">Select Date:</label>
                <input type="date" 
                       id="date-input" 
                       min="{min_date}" 
                       max="{max_date}" 
                       value="{default_date}"
                       style="padding: 5px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;">
                <button id="load-date-btn" 
                        style="padding: 6px 16px; 
                               background-color: #28a745; 
                               color: white; 
                               border: none; 
                               border-radius: 4px; 
                               font-size: 14px; 
                               font-weight: bold;
                               cursor: pointer;">
                    Load
                </button>
            </div>
            <div id="date-status" style="margin-top: 8px; font-size: 13px; color: #666;">
                Currently loaded: <span id="current-date" style="font-weight: bold; color: #333;">{default_date}</span>
            </div>
        </div>
        '''
    else:
        # Fallback to static timestamp display
        datepicker_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50%; transform: translateX(-50%);
                    background-color: white; border:2px solid grey; 
                    z-index:9999; font-size:16px;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;">
        Time: {default_timestamp}
        </div>
        '''
    
    m.get_root().html.add_child(folium.Element(datepicker_html))
    
    # Add minimap for navigation
    minimap = plugins.MiniMap(toggle_display=True)
    m.add_child(minimap)
    
    # Add fullscreen button
    plugins.Fullscreen(
        position='topleft',
        title='Fullscreen',
        title_cancel='Exit Fullscreen',
        force_separate_button=True
    ).add_to(m)
    
    # Add measure control
    plugins.MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(m)
    
    # Add JavaScript for date picker functionality
    if ENABLE_DATE_PICKER:
        # Prepare data for JavaScript
        available_timestamps = json.dumps(index['timestamps'])
        available_dates_js = json.dumps(available_dates)
        
        # Build GeoJSON files mapping
        geojson_files_map = {}
        for var_name in VARIABLES:
            if var_name in index['files']:
                geojson_files_map[var_name] = {}
                for i, timestamp in enumerate(index['timestamps']):
                    if i < len(index['files'][var_name]):
                        geojson_files_map[var_name][timestamp] = index['files'][var_name][i]
        
        geojson_files_js = json.dumps(geojson_files_map)
        variables_js = json.dumps(VARIABLES)
        
        javascript_code = f'''
        <script>
        // Data passed from Python
        const AVAILABLE_TIMESTAMPS = {available_timestamps};
        const AVAILABLE_DATES = {available_dates_js};
        const GEOJSON_FILES = {geojson_files_js};
        const VARIABLES = {variables_js};
        
        // Extract date from ISO timestamp
        function extractDate(timestamp) {{
            return timestamp.split('T')[0];
        }}
        
        // Find nearest available date
        function findNearestDate(targetDate, availableDates) {{
            if (!availableDates || availableDates.length === 0) {{
                return null;
            }}
            
            const target = new Date(targetDate);
            if (isNaN(target.getTime())) {{
                return availableDates[0];
            }}
            
            let nearest = availableDates[0];
            let minDiff = Math.abs(new Date(availableDates[0]) - target);
            
            for (let i = 1; i < availableDates.length; i++) {{
                const current = new Date(availableDates[i]);
                const diff = Math.abs(current - target);
                if (diff < minDiff) {{
                    minDiff = diff;
                    nearest = availableDates[i];
                }}
            }}
            
            return nearest;
        }}
        
        // Get timestamp for a specific date
        function getTimestampForDate(dateStr) {{
            for (let timestamp of AVAILABLE_TIMESTAMPS) {{
                if (extractDate(timestamp) === dateStr) {{
                    return timestamp;
                }}
            }}
            return null;
        }}
        
        // Get GeoJSON filename for variable and timestamp
        function getGeojsonFilename(varName, timestamp) {{
            if (GEOJSON_FILES[varName] && GEOJSON_FILES[varName][timestamp]) {{
                return GEOJSON_FILES[varName][timestamp];
            }}
            return null;
        }}
        
        // Main function to load data for selected date
        function loadDataForDate(selectedDate) {{
            console.log('Loading data for date:', selectedDate);
            
            // Validate date
            if (!selectedDate) {{
                alert('Please select a valid date.');
                return;
            }}
            
            // Find nearest available date
            const nearestDate = findNearestDate(selectedDate, AVAILABLE_DATES);
            
            if (!nearestDate) {{
                alert('No data available for the selected date.');
                return;
            }}
            
            // Get corresponding timestamp
            const timestamp = getTimestampForDate(nearestDate);
            
            if (!timestamp) {{
                alert('Could not find timestamp for date: ' + nearestDate);
                return;
            }}
            
            // Update UI
            document.getElementById('current-date').textContent = nearestDate;
            
            // Update input if nearest date is different
            if (nearestDate !== selectedDate) {{
                document.getElementById('date-input').value = nearestDate;
                console.log('Adjusted to nearest available date:', nearestDate);
            }}
            
            // Phase 1: UI update only
            // Phase 2 will implement actual marker loading here
            console.log('Date loaded successfully:', nearestDate);
            console.log('Timestamp:', timestamp);
            
            // Log available GeoJSON files for this timestamp
            VARIABLES.forEach(varName => {{
                const filename = getGeojsonFilename(varName, timestamp);
                console.log(varName + ' file:', filename);
            }});
        }}
        
        // Event listener for Load button
        document.getElementById('load-date-btn').addEventListener('click', function() {{
            const selectedDate = document.getElementById('date-input').value;
            loadDataForDate(selectedDate);
        }});
        
        // Event listener for Enter key on date input
        document.getElementById('date-input').addEventListener('keypress', function(event) {{
            if (event.key === 'Enter') {{
                const selectedDate = document.getElementById('date-input').value;
                loadDataForDate(selectedDate);
            }}
        }});
        
        // Auto-load on page load with default date
        window.addEventListener('load', function() {{
            const defaultDate = document.getElementById('date-input').value;
            console.log('Page loaded. Default date:', defaultDate);
            // Phase 1: Just log, don't actually reload
            // Phase 2 will load markers here
        }});
        </script>
        '''
        
        m.get_root().html.add_child(folium.Element(javascript_code))
    
    # Save map
    m.save(OUTPUT_FILE)
    print(f'✓ Map saved to {OUTPUT_FILE}')
    
    return m


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - Interactive Map with Date Picker')
    print('Phase 1 Implementation')
    print('=' * 70)
    
    # Check if GeoJSON directory exists
    if not os.path.exists(GEOJSON_DIR):
        print(f'\n✗ Error: {GEOJSON_DIR} directory not found')
        print('Please run A3_1_generate_geojson_from_netcdf.py first')
        return
    
    # Load timeseries index
    index = load_timeseries_index()
    if index is None:
        return
    
    # Create interactive map
    create_interactive_map(index)
    
    print('\n' + '=' * 70)
    print('✓ INTERACTIVE MAP CREATION COMPLETE!')
    print('=' * 70)
    print(f'\nOutput file: {OUTPUT_FILE}')
    print('Open this file in your web browser to view the interactive map.')
    print('\nFeatures:')
    print('  - Layer control: Toggle visibility of different variables')
    print('  - Circle markers: Size and color represent data values')
    print('  - Interactive tooltips: Click on markers for details')
    print('  - Multiple base maps: Switch between different map styles')
    print('  - Fullscreen mode: Click the fullscreen button')
    print('  - Date Picker: Select and load different dates (Phase 1)')
    print('\nPhase 1 Limitations:')
    print('  - Date selection updates UI but does not yet swap markers')
    print('  - Actual dynamic marker loading will be implemented in Phase 2')
    print('=' * 70)


if __name__ == '__main__':
    main()
