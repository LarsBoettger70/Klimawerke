'''
Interactive Map Builder with Dynamic Date Picker (Phase 2)
Loads pre-generated GeoJSON files and creates an interactive Folium map
with layer control and dynamic marker loading using date picker with Previous/Next buttons
'''

import folium
from folium import plugins
import json
import os
import numpy as np
from datetime import datetime

# Configuration
GEOJSON_DIR = 'geojson'
OUTPUT_FILE = 'interactive_map_with_dynamic_datepicker.html'

# Date Picker Configuration
DEFAULT_DATE_MODE = 'today'  # Options: 'today', 'first', or ISO date string (e.g., '2024-01-15')
ENABLE_DATE_PICKER = True
ENABLE_PREV_NEXT_BUTTONS = True
SHOW_FEATURE_COUNT = True
LOADING_ANIMATION = True

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
    if not timestamp or 'T' not in timestamp:
        return None
    return timestamp.split('T')[0]


def get_default_date(index, default_mode):
    '''
    Determine which date to load based on configuration
    
    Args:
        index: The timeseries index dictionary
        default_mode: 'today', 'first', or ISO date string
    
    Returns:
        ISO date string (YYYY-MM-DD) or None if no valid dates
    '''
    if not index or not index.get('timestamps'):
        return None
    
    # Extract dates, filtering out None values from malformed timestamps
    available_dates = [extract_date_from_timestamp(ts) for ts in index['timestamps']]
    available_dates = [d for d in available_dates if d is not None]
    
    if not available_dates:
        return None
    
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


def get_next_date(current_date, available_dates):
    '''
    Get the next available date after the current date
    
    Args:
        current_date: Current date string (YYYY-MM-DD)
        available_dates: Sorted list of available date strings
    
    Returns:
        Next date string or None if current is the last date
    '''
    try:
        current_idx = available_dates.index(current_date)
        if current_idx < len(available_dates) - 1:
            return available_dates[current_idx + 1]
    except (ValueError, IndexError):
        pass
    return None


def get_previous_date(current_date, available_dates):
    '''
    Get the previous available date before the current date
    
    Args:
        current_date: Current date string (YYYY-MM-DD)
        available_dates: Sorted list of available date strings
    
    Returns:
        Previous date string or None if current is the first date
    '''
    try:
        current_idx = available_dates.index(current_date)
        if current_idx > 0:
            return available_dates[current_idx - 1]
    except (ValueError, IndexError):
        pass
    return None


def load_all_geojson_files(index):
    '''
    Build a lookup dictionary of all GeoJSON filenames by date and variable
    
    Args:
        index: The timeseries index dictionary
    
    Returns:
        Dictionary with structure: {date: {variable: filename}}
    '''
    geojson_lookup = {}
    
    for timestamp in index['timestamps']:
        date = extract_date_from_timestamp(timestamp)
        if not date:
            continue
        
        if date not in geojson_lookup:
            geojson_lookup[date] = {}
        
        for var_name in VARIABLES:
            if var_name in index['files']:
                filename = get_geojson_files_for_timestamp(timestamp, index, var_name)
                if filename:
                    geojson_lookup[date][var_name] = filename
    
    return geojson_lookup


def create_layer_for_variable(m, var_name):
    '''
    Create a FeatureGroup layer for a specific variable
    Phase 2: Creates empty layer - markers loaded dynamically via JavaScript
    '''
    print(f'\nCreating layer for {var_name}...')
    
    config = COLOR_SCALES[var_name]
    feature_group = folium.FeatureGroup(name=config['name'], show=True)
    
    # Phase 2: Don't pre-load markers - they will be loaded dynamically
    # Just create the empty feature group
    feature_group.add_to(m)
    
    print(f'✓ Created empty layer for {var_name} (markers will be loaded dynamically)')
    return feature_group


def create_interactive_map(index):
    '''
    Create the main interactive map with all layers and controls
    '''
    print('\nCreating interactive map...')
    
    # Extract available dates for the date picker (filter out None values)
    available_dates = [extract_date_from_timestamp(ts) for ts in index['timestamps']]
    available_dates = [d for d in available_dates if d is not None]
    
    if not available_dates:
        print('✗ Error: No valid dates found in timeseries index')
        return None
    
    # Determine default date to load
    default_date = get_default_date(index, DEFAULT_DATE_MODE)
    if not default_date:
        default_date = available_dates[0]  # Fallback to first date
    
    default_timestamp = get_timestamp_for_date(default_date, index)
    if not default_timestamp:
        default_timestamp = index['timestamps'][0]  # Fallback to first timestamp
    
    print(f'Default date: {default_date}')
    print(f'Default timestamp: {default_timestamp}')
    
    # Get min and max dates for date picker constraints
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
    
    for var_name in VARIABLES:
        if var_name in index['files']:
            layer = create_layer_for_variable(m, var_name)
            layers[var_name] = layer
    
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
        # Phase 2: Add Previous/Next buttons
        if ENABLE_PREV_NEXT_BUTTONS:
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
                    <button id="prevBtn" 
                            style="padding: 6px 12px; 
                                   background-color: #2196F3; 
                                   color: white; 
                                   border: none; 
                                   border-radius: 4px; 
                                   font-size: 14px; 
                                   font-weight: bold;
                                   cursor: pointer;">
                        ◀ Previous
                    </button>
                    <input type="date" 
                           id="dateInput" 
                           min="{min_date}" 
                           max="{max_date}" 
                           value="{default_date}"
                           style="padding: 5px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;">
                    <button id="nextBtn" 
                            style="padding: 6px 12px; 
                                   background-color: #2196F3; 
                                   color: white; 
                                   border: none; 
                                   border-radius: 4px; 
                                   font-size: 14px; 
                                   font-weight: bold;
                                   cursor: pointer;">
                        Next ▶
                    </button>
                    <button id="loadBtn" 
                            style="padding: 6px 16px; 
                                   background-color: #4CAF50; 
                                   color: white; 
                                   border: none; 
                                   border-radius: 4px; 
                                   font-size: 14px; 
                                   font-weight: bold;
                                   cursor: pointer;">
                        Load
                    </button>
                    <span id="loadingIndicator" style="display: none; margin-left: 10px;">
                        <svg width="20" height="20" viewBox="0 0 50 50" style="animation: spin 1s linear infinite;">
                            <circle cx="25" cy="25" r="20" fill="none" stroke="#2196F3" stroke-width="5" stroke-dasharray="31.4 31.4" stroke-linecap="round" />
                        </svg>
                    </span>
                </div>
                <div id="dateStatus" style="margin-top: 8px; font-size: 13px; color: #666;">
                    Loaded: <span id="currentDateDisplay" style="font-weight: bold; color: #333;">{default_date}</span> 
                    <span id="featureCount" style="margin-left: 10px;">(0 features)</span>
                </div>
            </div>
            <style>
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                #prevBtn:disabled, #nextBtn:disabled {{
                    opacity: 0.5;
                    cursor: not-allowed;
                }}
            </style>
            '''
        else:
            # Phase 1 style (no prev/next buttons)
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
        color_scales_js = json.dumps(COLOR_SCALES)
        default_date_js = json.dumps(default_date)
        geojson_dir_js = json.dumps(GEOJSON_DIR)
        
        javascript_code = f'''
        <script>
        // Data passed from Python
        const AVAILABLE_TIMESTAMPS = {available_timestamps};
        const AVAILABLE_DATES = {available_dates_js};
        const GEOJSON_FILES = {geojson_files_js};
        const GEOJSON_DIR = {geojson_dir_js};
        const VARIABLES = {variables_js};
        const COLOR_SCALES = {color_scales_js};
        const DEFAULT_DATE = {default_date_js};
        
        // State variables
        let currentDate = DEFAULT_DATE;
        let currentTimestamp = null;
        let currentLoadedFeatures = 0;
        let leafletLayers = {{}};  // Store marker references for each variable
        let layerGroups = {{}};  // Cache layer group references for performance
        
        // Initialize layer references from Folium's layer control
        function initializeLayerReferences() {{
            // Get all overlay layers created by Folium
            const map = window.map_obj;
            if (!map || !map._layers) return;
            
            // Cache layer group references for each variable
            VARIABLES.forEach(varName => {{
                leafletLayers[varName] = [];
                
                // Find and cache the layer group for this variable
                Object.values(map._layers).forEach(layer => {{
                    if (layer.options && layer.options.name === COLOR_SCALES[varName].name) {{
                        layerGroups[varName] = layer;
                    }}
                }});
            }});
            
            console.log('Layer groups cached:', Object.keys(layerGroups));
        }}
        
        // Extract date from ISO timestamp
        function extractDate(timestamp) {{
            return timestamp.split('T')[0];
        }}
        
        // Get next available date
        function getNextDate(currentDate) {{
            const currentIdx = AVAILABLE_DATES.indexOf(currentDate);
            if (currentIdx >= 0 && currentIdx < AVAILABLE_DATES.length - 1) {{
                return AVAILABLE_DATES[currentIdx + 1];
            }}
            return null;
        }}
        
        // Get previous available date
        function getPreviousDate(currentDate) {{
            const currentIdx = AVAILABLE_DATES.indexOf(currentDate);
            if (currentIdx > 0) {{
                return AVAILABLE_DATES[currentIdx - 1];
            }}
            return null;
        }}
        
        // Select date without loading (just updates input and buttons)
        function selectDate(newDate) {{
            if (!newDate) return;
            currentDate = newDate;
            document.getElementById('dateInput').value = newDate;
            updateButtonStates();
        }}
        
        // Update button states (enable/disable at boundaries)
        function updateButtonStates() {{
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            
            if (prevBtn && nextBtn) {{
                prevBtn.disabled = (getPreviousDate(currentDate) === null);
                nextBtn.disabled = (getNextDate(currentDate) === null);
            }}
        }}
        
        // Show loading indicator
        function showLoadingIndicator() {{
            const indicator = document.getElementById('loadingIndicator');
            if (indicator) {{
                indicator.style.display = 'inline-block';
            }}
        }}
        
        // Hide loading indicator
        function hideLoadingIndicator() {{
            const indicator = document.getElementById('loadingIndicator');
            if (indicator) {{
                indicator.style.display = 'none';
            }}
        }}
        
        // Get GeoJSON filename for variable and timestamp
        function getGeojsonFilenameForTimestamp(varName, timestamp) {{
            if (GEOJSON_FILES[varName] && GEOJSON_FILES[varName][timestamp]) {{
                return GEOJSON_FILES[varName][timestamp];
            }}
            return null;
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
        
        // Value to color conversion
        function valueToColor(value, colors, vmin, vmax) {{
            if (isNaN(value) || value === null) {{
                return '#808080';  // Gray for NaN
            }}
            
            // Normalize value to 0-1
            let normalized = (value - vmin) / (vmax - vmin);
            normalized = Math.max(0, Math.min(1, normalized));  // Clamp to 0-1
            
            // Get color index
            const idx = Math.floor(normalized * (colors.length - 1));
            return colors[idx];
        }}
        
        // Value to radius conversion
        function valueToRadius(value, vmin, vmax, minRadius = 2, maxRadius = 10) {{
            if (isNaN(value) || value === null) {{
                return minRadius;
            }}
            
            // Normalize value to 0-1
            let normalized = (value - vmin) / (vmax - vmin);
            normalized = Math.max(0, Math.min(1, normalized));  // Clamp to 0-1
            
            // Linear interpolation
            return minRadius + normalized * (maxRadius - minRadius);
        }}
        
        // Create a Leaflet marker for a feature
        function createLeafletMarker(feature, varName, timestamp) {{
            const value = feature.properties.value;
            const lat = feature.geometry.coordinates[1];
            const lon = feature.geometry.coordinates[0];
            
            const config = COLOR_SCALES[varName];
            const color = valueToColor(value, config.colors, config.vmin, config.vmax);
            const radius = valueToRadius(value, config.vmin, config.vmax);
            
            // Create popup text
            const popupText = `
                <b>${{config.name}}</b><br>
                Value: ${{value.toFixed(2)}}<br>
                Lat: ${{lat.toFixed(2)}}°<br>
                Lon: ${{lon.toFixed(2)}}°<br>
                Time: ${{timestamp}}
            `;
            
            // Create CircleMarker
            const marker = L.circleMarker([lat, lon], {{
                radius: radius,
                color: color,
                fillColor: color,
                fillOpacity: 0.7,
                weight: 1
            }}).bindPopup(popupText, {{maxWidth: 250}});
            
            return marker;
        }}
        
        // Clear all markers for a variable
        function clearVariableMarkers(varName) {{
            if (leafletLayers[varName]) {{
                leafletLayers[varName].forEach(marker => {{
                    if (marker && marker.remove) {{
                        marker.remove();
                    }}
                }});
                leafletLayers[varName] = [];
            }}
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
        
        // Main function to load data for a date
        async function loadDataForDate(dateStr) {{
            console.log('Loading data for date:', dateStr);
            
            // Validate date
            if (!dateStr) {{
                alert('Please select a valid date.');
                return;
            }}
            
            // Find nearest available date
            const nearestDate = findNearestDate(dateStr, AVAILABLE_DATES);
            
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
            
            // Update current state
            currentDate = nearestDate;
            currentTimestamp = timestamp;
            
            // Update input if nearest date is different
            if (nearestDate !== dateStr) {{
                document.getElementById('dateInput').value = nearestDate;
                console.log('Adjusted to nearest available date:', nearestDate);
            }}
            
            // Show loading indicator
            showLoadingIndicator();
            
            // Track total features loaded
            let totalFeatures = 0;
            
            // Load data for each variable
            for (const varName of VARIABLES) {{
                // Clear previous markers for this variable
                clearVariableMarkers(varName);
                
                // Get GeoJSON filename
                const filename = getGeojsonFilenameForTimestamp(varName, timestamp);
                
                if (!filename) {{
                    console.warn(`No GeoJSON file found for ${{varName}} at ${{timestamp}}`);
                    continue;
                }}
                
                // Fetch GeoJSON file
                const geojsonPath = `${{GEOJSON_DIR}}/${{filename}}`;
                
                try {{
                    const response = await fetch(geojsonPath);
                    
                    if (!response.ok) {{
                        console.error(`Failed to fetch ${{geojsonPath}}: ${{response.status}}`);
                        continue;
                    }}
                    
                    const geojsonData = await response.json();
                    
                    // Create markers for each feature
                    const features = geojsonData.features || [];
                    totalFeatures += features.length;
                    
                    // Use cached layer group for this variable
                    const layerGroup = layerGroups[varName];
                    
                    if (layerGroup) {{
                        features.forEach(feature => {{
                            const marker = createLeafletMarker(feature, varName, timestamp);
                            marker.addTo(layerGroup);
                            leafletLayers[varName].push(marker);
                        }});
                    }} else {{
                        console.warn(`Could not find layer group for ${{varName}}`);
                    }}
                    
                    console.log(`Loaded ${{features.length}} features for ${{varName}}`);
                    
                }} catch (error) {{
                    console.error(`Error loading ${{geojsonPath}}:`, error);
                }}
            }}
            
            // Update UI
            document.getElementById('currentDateDisplay').textContent = nearestDate;
            document.getElementById('featureCount').textContent = `(${{totalFeatures}} features)`;
            
            currentLoadedFeatures = totalFeatures;
            
            // Update button states
            updateButtonStates();
            
            // Hide loading indicator
            hideLoadingIndicator();
            
            console.log('Date loaded successfully:', nearestDate);
            console.log('Total features loaded:', totalFeatures);
        }}
        
        // Event Listeners
        document.addEventListener('DOMContentLoaded', function() {{
            // Get map object reference
            // Folium creates a global variable for the map
            setTimeout(() => {{
                // Find the map object in the global scope
                for (let key in window) {{
                    if (window[key] && window[key]._leaflet_id && window[key]._layers) {{
                        window.map_obj = window[key];
                        console.log('Found map object:', key);
                        break;
                    }}
                }}
                
                initializeLayerReferences();
                updateButtonStates();
                
                // Load default date
                loadDataForDate(DEFAULT_DATE);
            }}, 500);
            
            // Previous button
            const prevBtn = document.getElementById('prevBtn');
            if (prevBtn) {{
                prevBtn.addEventListener('click', function() {{
                    const prevDate = getPreviousDate(currentDate);
                    if (prevDate) {{
                        selectDate(prevDate);
                    }}
                }});
            }}
            
            // Next button
            const nextBtn = document.getElementById('nextBtn');
            if (nextBtn) {{
                nextBtn.addEventListener('click', function() {{
                    const nextDate = getNextDate(currentDate);
                    if (nextDate) {{
                        selectDate(nextDate);
                    }}
                }});
            }}
            
            // Load button
            const loadBtn = document.getElementById('loadBtn');
            if (loadBtn) {{
                loadBtn.addEventListener('click', function() {{
                    const selectedDate = document.getElementById('dateInput').value;
                    loadDataForDate(selectedDate);
                }});
            }}
            
            // Date input change
            const dateInput = document.getElementById('dateInput');
            if (dateInput) {{
                dateInput.addEventListener('change', function(e) {{
                    selectDate(e.target.value);
                }});
                
                // Enter key on date input
                dateInput.addEventListener('keypress', function(event) {{
                    if (event.key === 'Enter') {{
                        loadDataForDate(this.value);
                    }}
                }});
            }}
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
    print('Phase 2 Implementation - Dynamic Marker Loading')
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
    print('  - Date Picker with Previous/Next buttons (Phase 2)')
    print('  - Dynamic marker loading: GeoJSON files loaded on-demand')
    print('  - Feature count display: Shows number of loaded features')
    print('  - Loading animation: Visual feedback during data loading')
    print('\nPhase 2 Features:')
    print('  - Previous/Next buttons for easy date navigation')
    print('  - Load button to fetch and display markers for selected date')
    print('  - Buttons disabled at date boundaries')
    print('  - Real-time feature count updates')
    print('  - GeoJSON files loaded dynamically from geojson/ folder')
    print('  - Reduced initial page size (markers not embedded)')
    print('=' * 70)


if __name__ == '__main__':
    main()
