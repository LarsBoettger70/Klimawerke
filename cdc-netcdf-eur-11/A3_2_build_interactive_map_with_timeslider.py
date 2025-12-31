'''
Interactive Map Builder with TimeSlider
Loads pre-generated GeoJSON files and creates an interactive Folium map
with layer control and time slider functionality
'''

import folium
from folium import plugins
import json
import os
import numpy as np

# Configuration
GEOJSON_DIR = 'geojson'
OUTPUT_FILE = 'interactive_map_with_timeslider.html'

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
    
    for var_name in ['swh', 't2m', 'tp', 'wind_speed', 'sst']:
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
    
    # Add timestamp display
    timestamp_html = f'''
    <div style="position: fixed; 
                top: 10px; left: 50%; transform: translateX(-50%);
                background-color: white; border:2px solid grey; 
                z-index:9999; font-size:16px;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;">
    Time: {index['timestamps'][0] if index['timestamps'] else 'N/A'}
    </div>
    '''
    m.get_root().html.add_child(folium.Element(timestamp_html))
    
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
    
    # Save map
    m.save(OUTPUT_FILE)
    print(f'✓ Map saved to {OUTPUT_FILE}')
    
    return m


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - Interactive Map Builder')
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
    print('=' * 70)


if __name__ == '__main__':
    main()
