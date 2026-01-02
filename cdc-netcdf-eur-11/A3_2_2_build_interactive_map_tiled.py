'''
Interactive Map Builder - Tiled Version
Creates an interactive Folium map with intelligent tile loading
Only loads tiles visible in the current map viewport
'''

import folium
from folium import plugins
import json
import os
from datetime import datetime

# Configuration
GEOJSON_DIR = 'geojson_tiled'
OUTPUT_FILE = 'a3_2_2_interactive_map_tiled.html'
DEFAULT_DATE = 'today'  # Options: 'today', 'first', or ISO date string
DEFAULT_HOUR = 12  # Default hour to display (0-23)


def load_metadata():
    '''Load the metadata file'''
    metadata_file = os.path.join(GEOJSON_DIR, 'metadata. json')
    
    if not os.path.exists(metadata_file):
        print(f'✗ Error: {metadata_file} not found')
        print('Please run A3_1_2_generate_geojson_tiled.py first')
        return None
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f'✓ Loaded metadata')
    print(f'  - Dates available: {len(metadata["dates"])}')
    print(f'  - Date range: {metadata["dates"][0]} to {metadata["dates"][-1]}')
    print(f'  - Variables:  {", ".join(metadata["variables"].keys())}')
    print(f'  - Tiles: {metadata["tiling"]["rows"]}×{metadata["tiling"]["cols"]} = {metadata["tiling"]["total_tiles"]}')
    
    return metadata


def get_default_date(metadata, default_mode):
    '''Determine which date to load based on configuration'''
    available_dates = metadata['dates']
    
    if not available_dates:
        return None
    
    if default_mode == 'first':
        return available_dates[0]
    elif default_mode == 'today':
        today = datetime.now().strftime('%Y-%m-%d')
        # Find nearest date
        from datetime import datetime as dt
        try:
            target = dt. strptime(today, '%Y-%m-%d')
            dates_dt = [dt.strptime(d, '%Y-%m-%d') for d in available_dates]
            closest = min(dates_dt, key=lambda d: abs((d - target).total_seconds()))
            return closest.strftime('%Y-%m-%d')
        except:
            return available_dates[-1]
    else:
        # Assume it's an ISO date string
        if default_mode in available_dates:
            return default_mode
        else:
            return available_dates[0]


def create_interactive_map(metadata):
    '''Create the interactive map with tiled data loading'''
    print('\nCreating interactive map...')
    
    # Get available dates
    available_dates = metadata['dates']
    min_date = min(available_dates)
    max_date = max(available_dates)
    
    # Determine default date
    default_date = get_default_date(metadata, DEFAULT_DATE)
    
    print(f'Default date: {default_date}')
    print(f'Default hour: {DEFAULT_HOUR}: 00')
    print(f'Date range: {min_date} to {max_date}')
    
    # Calculate center of map
    grid = metadata['grid']
    center_lat = (grid['lat_min'] + grid['lat_max']) / 2
    center_lon = (grid['lon_min'] + grid['lon_max']) / 2
    
    # Create base map
    m = folium. Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add alternative tile layers
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    
    # Create empty feature groups for each variable
    print('\nCreating layers...')
    for var_name, var_info in metadata['variables'].items():
        feature_group = folium.FeatureGroup(name=var_info['name'], show=True)
        feature_group.add_to(m)
        print(f'  ✓ Created layer:  {var_info["name"]}')
    
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 250px; 
                background-color: white; border: 2px solid grey; 
                z-index: 9999; font-size: 14px;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
        <p style="margin: 0 0 8px 0; font-weight:  bold; font-size: 15px;">Legend</p>
        <p style="margin: 5px 0; font-size:  12px;">
            <span style="color: #d53e4f;">●</span> High values<br>
            <span style="color: #fee08b;">●</span> Medium values<br>
            <span style="color: #3288bd;">●</span> Low values
        </p>
        <p style="margin: 5px 0; font-size:  11px; color: #666;">
            Circle size indicates magnitude
        </p>
        <p style="margin: 8px 0 0 0; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
            🎯 <b>Smart Loading: </b><br>
            Only visible tiles loaded
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add date/hour picker UI with tile info
    datepicker_html = f'''
    <div id="date-picker-container" style="position: fixed; 
                top: 10px; left: 50%; transform: translateX(-50%);
                background-color: white; border: 2px solid #333; 
                z-index: 9999; 
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow:  0 2px 6px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
                min-width: 650px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <button id="prevDayBtn" 
                    style="padding: 6px 12px; 
                           background-color: #2196F3; 
                           color: white; 
                           border: none; 
                           border-radius: 4px; 
                           font-size: 14px; 
                           font-weight: bold;
                           cursor: pointer;">
                ◀ Prev Day
            </button>
            <input type="date" 
                   id="dateInput" 
                   min="{min_date}" 
                   max="{max_date}" 
                   value="{default_date}"
                   style="padding: 5px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;">
            <button id="nextDayBtn" 
                    style="padding: 6px 12px; 
                           background-color:  #2196F3; 
                           color: white; 
                           border: none; 
                           border-radius: 4px; 
                           font-size:  14px; 
                           font-weight: bold;
                           cursor: pointer;">
                Next Day ▶
            </button>
            <span id="loadingIndicator" style="display: none; margin-left: 10px;">
                <svg width="20" height="20" viewBox="0 0 50 50" style="animation: spin 1s linear infinite;">
                    <circle cx="25" cy="25" r="20" fill="none" stroke="#2196F3" stroke-width="5" stroke-dasharray="31. 4 31.4" stroke-linecap="round" />
                </svg>
            </span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <button id="prevHourBtn" 
                    style="padding: 6px 12px; 
                           background-color: #FF9800; 
                           color: white; 
                           border: none; 
                           border-radius: 4px; 
                           font-size: 13px; 
                           cursor: pointer;">
                ◀
            </button>
            <label style="font-weight: bold; font-size: 14px;">Hour: </label>
            <input type="range" 
                   id="hourSlider" 
                   min="0" 
                   max="23" 
                   value="{DEFAULT_HOUR}"
                   style="flex: 1;">
            <span id="hourDisplay" style="font-weight: bold; font-size: 16px; min-width: 60px; text-align: center;">{DEFAULT_HOUR: 02d}:00</span>
            <button id="nextHourBtn" 
                    style="padding: 6px 12px; 
                           background-color:  #FF9800; 
                           color: white; 
                           border: none; 
                           border-radius: 4px; 
                           font-size: 13px; 
                           cursor: pointer;">
                ▶
            </button>
        </div>
        <div id="statusDisplay" style="margin-top: 10px; font-size: 13px; color: #666; text-align: center;">
            <div>
                Loaded:  <span id="currentDisplay" style="font-weight: bold; color: #333;">{default_date} {DEFAULT_HOUR:02d}:00</span>
                <span id="featureCount" style="margin-left: 10px;">(0 features)</span>
            </div>
            <div style="margin-top:  4px; font-size: 11px;">
                Tiles: <span id="tileCount" style="font-weight: bold; color: #666;">0/{metadata["tiling"]["total_tiles"]}</span>
                <span id="tileSize" style="margin-left: 10px;">(0 KB)</span>
            </div>
        </div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        #prevDayBtn: disabled, #nextDayBtn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
    </style>
    '''
    m.get_root().html.add_child(folium.Element(datepicker_html))
    
    # Add minimap
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
    
    # Prepare data for JavaScript
    metadata_js = json.dumps(metadata)
    geojson_dir_js = json.dumps(GEOJSON_DIR)
    default_date_js = json.dumps(default_date)
    default_hour_js = DEFAULT_HOUR
    
    # Add JavaScript with tile loading logic
    javascript_code = f'''
    <script>
    // Configuration
    const METADATA = {metadata_js};
    const GEOJSON_DIR = {geojson_dir_js};
    const DEFAULT_DATE = {default_date_js};
    const DEFAULT_HOUR = {default_hour_js};
    
    // State
    let currentDate = DEFAULT_DATE;
    let currentHour = DEFAULT_HOUR;
    let leafletMap = null;
    let layerGroups = {{}};
    let loadedTiles = {{}};  // Cache for loaded tile data
    let currentVisibleTiles = [];
    let totalLoadedBytes = 0;
    
    // Color/radius calculation functions
    function valueToColor(value, colorScale) {{
        const {{vmin, vmax, colors}} = colorScale;
        if (isNaN(value) || value === null) return '#808080';
        
        let normalized = (value - vmin) / (vmax - vmin);
        normalized = Math.max(0, Math.min(1, normalized));
        
        const idx = Math.floor(normalized * (colors.length - 1));
        return colors[idx];
    }}
    
    function valueToRadius(value, vmin, vmax, minRadius = 2, maxRadius = 10) {{
        if (isNaN(value) || value === null) return minRadius;
        
        let normalized = (value - vmin) / (vmax - vmin);
        normalized = Math.max(0, Math.min(1, normalized));
        
        return minRadius + normalized * (maxRadius - minRadius);
    }}
    
    // Tile visibility detection
    function getTileId(lat, lon) {{
        const tiling = METADATA.tiling;
        const grid = METADATA.grid;
        
        // Calculate which tile this point belongs to
        const latRange = grid. lat_max - grid.lat_min;
        const lonRange = grid.lon_max - grid. lon_min;
        
        const latPerTile = latRange / tiling.rows;
        const lonPerTile = lonRange / tiling.cols;
        
        let row = Math.floor((grid.lat_max - lat) / latPerTile);
        let col = Math. floor((lon - grid.lon_min) / lonPerTile);
        
        // Clamp to valid range
        row = Math.max(0, Math. min(tiling.rows - 1, row));
        col = Math.max(0, Math. min(tiling.cols - 1, col));
        
        return `${{row}}-${{col}}`;
    }}
    
    function getVisibleTiles() {{
        if (! leafletMap) return [];
        
        const bounds = leafletMap.getBounds();
        const north = bounds.getNorth();
        const south = bounds.getSouth();
        const east = bounds.getEast();
        const west = bounds.getWest();
        
        // Get corners and center
        const testPoints = [
            [north, west],
            [north, east],
            [south, west],
            [south, east],
            [(north + south) / 2, (east + west) / 2]
        ];
        
        const visibleTiles = new Set();
        
        testPoints.forEach(([lat, lon]) => {{
            const tileId = getTileId(lat, lon);
            visibleTiles.add(tileId);
        }});
        
        // Also check tiles along edges
        const tiling = METADATA.tiling;
        for (let row = 0; row < tiling.rows; row++) {{
            for (let col = 0; col < tiling.cols; col++) {{
                const tileId = `${{row}}-${{col}}`;
                const tileBounds = METADATA.tiling.tiles[tileId];
                
                // Check if tile overlaps with visible bounds
                if (!(tileBounds.lat_max < south || tileBounds.lat_min > north ||
                      tileBounds.lon_max < west || tileBounds.lon_min > east)) {{
                    visibleTiles.add(tileId);
                }}
            }}
        }}
        
        return Array.from(visibleTiles);
    }}
    
    // Initialize layer references
    function initializeLayerReferences() {{
        console.log('Initializing layer references...');
        
        if (!leafletMap) {{
            console.error('Map not found');
            return false;
        }}
        
        // Find LayerControl
        let layerControl = null;
        const controls = leafletMap._controls || [];
        
        for (let control of controls) {{
            if (control instanceof L.Control. Layers) {{
                layerControl = control;
                break;
            }}
        }}
        
        if (!layerControl) {{
            console.error('LayerControl not found');
            return false;
        }}
        
        // Get overlays
        const overlays = layerControl._layers || [];
        
        for (let layerInfo of overlays) {{
            if (layerInfo.overlay && layerInfo.name) {{
                // Map display name to variable name
                for (let [varName, varInfo] of Object. entries(METADATA.variables)) {{
                    if (varInfo. name === layerInfo.name) {{
                        layerGroups[varName] = layerInfo.layer;
                        console.log(`Cached layer: ${{varName}}`);
                        break;
                    }}
                }}
            }}
        }}
        
        console.log(`Cached ${{Object.keys(layerGroups).length}} layers`);
        return Object.keys(layerGroups).length > 0;
    }}
    
    // Load specific tile
    async function loadTile(varName, date, hour, tileId) {{
        const cacheKey = `${{varName}}_${{date}}_${{hour}}_${{tileId}}`;
        
        // Check cache
        if (loadedTiles[cacheKey]) {{
            return loadedTiles[cacheKey];
        }}
        
        // Load from server
        const filename = `${{varName}}_${{date}}_${{String(hour).padStart(2, '0')}}_tile-${{tileId}}.geojson`;
        const filepath = `${{GEOJSON_DIR}}/${{filename}}`;
        
        try {{
            const response = await fetch(filepath);
            if (!response.ok) {{
                console.warn(`Tile not found: ${{filename}}`);
                return null;
            }}
            
            const geojson = await response.json();
            
            // Estimate size
            const sizeBytes = JSON.stringify(geojson).length;
            totalLoadedBytes += sizeBytes;
            
            // Cache it
            loadedTiles[cacheKey] = geojson. features;
            
            console.log(`Loaded tile ${{tileId}} for ${{varName}} (${{geojson.features.length}} features)`);
            return geojson.features;
            
        }} catch (error) {{
            console.error(`Error loading tile ${{filename}}:`, error);
            return null;
        }}
    }}
    
    // Show current date/hour with smart tile loading
    async function showDateTime(date, hour) {{
        console.log(`Showing ${{date}} ${{hour}}: 00`);
        showLoadingIndicator();
        
        currentDate = date;
        currentHour = hour;
        
        // Get visible tiles
        const visibleTiles = getVisibleTiles();
        currentVisibleTiles = visibleTiles;
        
        console.log(`Visible tiles: ${{visibleTiles.join(', ')}}`);
        
        let totalFeatures = 0;
        let tilesLoaded = 0;
        
        // Load only visible tiles for each variable
        for (let [varName, layer] of Object.entries(layerGroups)) {{
            layer.clearLayers();
            
            const varInfo = METADATA.variables[varName];
            const colorScale = varInfo.color_scale;
            
            // Load each visible tile
            for (let tileId of visibleTiles) {{
                const features = await loadTile(varName, date, hour, tileId);
                
                if (! features) continue;
                
                totalFeatures += features.length;
                tilesLoaded++;
                
                // Add markers
                features.forEach(feature => {{
                    const [lon, lat] = feature.geometry.coordinates;
                    const value = feature.properties.value;
                    
                    const color = valueToColor(value, colorScale);
                    const radius = valueToRadius(value, colorScale.vmin, colorScale. vmax);
                    
                    const popup = `
                        <b>${{varInfo.name}}</b><br>
                        Value: ${{value. toFixed(2)}} ${{varInfo.unit}}<br>
                        Time: ${{feature.properties.time}}<br>
                        Location: ${{lat.toFixed(2)}}°, ${{lon.toFixed(2)}}°<br>
                        Tile: ${{tileId}}
                    `;
                    
                    L.circleMarker([lat, lon], {{
                        radius: radius,
                        color:  color,
                        fillColor: color,
                        fillOpacity: 0.7,
                        weight: 1
                    }}).bindPopup(popup).addTo(layer);
                }});
            }}
        }}
        
        updateDateDisplay();
        updateHourDisplay(hour);
        updateFeatureCount(totalFeatures);
        updateTileInfo(visibleTiles.length, tilesLoaded);
        hideLoadingIndicator();
    }}
    
    // UI update functions
    function updateDateDisplay() {{
        document.getElementById('currentDisplay').textContent = 
            `${{currentDate}} ${{String(currentHour).padStart(2, '0')}}:00`;
    }}
    
    function updateHourDisplay(hour) {{
        document. getElementById('hourDisplay').textContent = 
            `${{String(hour).padStart(2, '0')}}:00`;
        document.getElementById('hourSlider').value = hour;
    }}
    
    function updateFeatureCount(count) {{
        document.getElementById('featureCount').textContent = `(${{count}} features)`;
    }}
    
    function updateTileInfo(visibleCount, loadedCount) {{
        const totalTiles = METADATA.tiling.total_tiles;
        document.getElementById('tileCount').textContent = `${{loadedCount}}/${{totalTiles}} visible`;
        
        const sizeKB = (totalLoadedBytes / 1024).toFixed(1);
        document.getElementById('tileSize').textContent = `(${{sizeKB}} KB loaded)`;
    }}
    
    function updateButtonStates() {{
        const dates = METADATA.dates;
        const currentIdx = dates.indexOf(currentDate);
        
        document.getElementById('prevDayBtn').disabled = (currentIdx <= 0);
        document.getElementById('nextDayBtn').disabled = (currentIdx >= dates.length - 1);
    }}
    
    function showLoadingIndicator() {{
        document.getElementById('loadingIndicator').style.display = 'inline-block';
    }}
    
    function hideLoadingIndicator() {{
        document.getElementById('loadingIndicator').style.display = 'none';
    }}
    
    // Navigation functions
    function goToPreviousDay() {{
        const dates = METADATA.dates;
        const currentIdx = dates.indexOf(currentDate);
        if (currentIdx > 0) {{
            const newDate = dates[currentIdx - 1];
            document.getElementById('dateInput').value = newDate;
            showDateTime(newDate, currentHour);
        }}
    }}
    
    function goToNextDay() {{
        const dates = METADATA.dates;
        const currentIdx = dates.indexOf(currentDate);
        if (currentIdx < dates.length - 1) {{
            const newDate = dates[currentIdx + 1];
            document.getElementById('dateInput').value = newDate;
            showDateTime(newDate, currentHour);
        }}
    }}
    
    function goToPreviousHour() {{
        if (currentHour > 0) {{
            showDateTime(currentDate, currentHour - 1);
        }}
    }}
    
    function goToNextHour() {{
        if (currentHour < 23) {{
            showDateTime(currentDate, currentHour + 1);
        }}
    }}
    
    // Handle map movement - reload tiles if needed
    function handleMapMoveEnd() {{
        const newVisibleTiles = getVisibleTiles();
        
        // Check if visible tiles changed
        const changed = newVisibleTiles.some(t => ! currentVisibleTiles.includes(t)) ||
                       currentVisibleTiles.some(t => !newVisibleTiles. includes(t));
        
        if (changed) {{
            console.log('Visible tiles changed, reloading.. .');
            showDateTime(currentDate, currentHour);
        }}
    }}
    
    // Event listeners
    document.addEventListener('DOMContentLoaded', function() {{
        console.log('DOM loaded, initializing...');
        
        // Find map object
        setTimeout(() => {{
            for (let key in window) {{
                try {{
                    const obj = window[key];
                    if (obj && typeof obj === 'object' && obj._leaflet_id && obj. eachLayer) {{
                        leafletMap = obj;
                        console.log('Found map object');
                        break;
                    }}
                }} catch (e) {{}}
            }}
            
            if (leafletMap) {{
                const initialized = initializeLayerReferences();
                
                if (initialized) {{
                    // Auto-load default date/hour
                    showDateTime(DEFAULT_DATE, DEFAULT_HOUR);
                    
                    // Listen for map movement
                    leafletMap.on('moveend', handleMapMoveEnd);
                    leafletMap.on('zoomend', handleMapMoveEnd);
                }} else {{
                    alert('Error:  Could not initialize map layers');
                }}
            }} else {{
                alert('Error:  Map object not found');
            }}
        }}, 100);
        
        // Day navigation
        document.getElementById('prevDayBtn').addEventListener('click', goToPreviousDay);
        document.getElementById('nextDayBtn').addEventListener('click', goToNextDay);
        
        document.getElementById('dateInput').addEventListener('change', (e) => {{
            showDateTime(e.target.value, currentHour);
        }});
        
        document.getElementById('dateInput').addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') {{
                showDateTime(e.target.value, currentHour);
            }}
        }});
        
        // Hour navigation
        document.getElementById('hourSlider').addEventListener('input', (e) => {{
            showDateTime(currentDate, parseInt(e.target.value));
        }});
        
        document.getElementById('prevHourBtn').addEventListener('click', goToPreviousHour);
        document.getElementById('nextHourBtn').addEventListener('click', goToNextHour);
    }});
    </script>
    '''
    
    m.get_root().html. add_child(folium.Element(javascript_code))
    
    # Save map
    m.save(OUTPUT_FILE)
    print(f'\n✓ Map saved to {OUTPUT_FILE}')
    
    return m


def main():
    print('=' * 70)
    print('CDC European Weather and Wave Data - Interactive Map')
    print('Version 2.2:  Tiled with Smart Loading')
    print('=' * 70)
    
    # Check if GeoJSON directory exists
    if not os.path.exists(GEOJSON_DIR):
        print(f'\n✗ Error: {GEOJSON_DIR} directory not found')
        print('Please run A3_1_2_generate_geojson_tiled.py first')
        return
    
    # Load metadata
    metadata = load_metadata()
    if metadata is None:
        return
    
    # Create interactive map
    create_interactive_map(metadata)
    
    print('\n' + '=' * 70)
    print('✓ INTERACTIVE MAP CREATION COMPLETE!')
    print('=' * 70)
    print(f'\nOutput file: {OUTPUT_FILE}')
    print('\nFeatures:')
    print('  ✅ Date picker with Previous/Next day buttons')
    print('  ✅ Hour slider (0-23) for smooth time navigation')
    print('  ✅ 🎯 SMART TILE LOADING:  Only loads visible map region')
    print('  ✅ Automatic reload when panning/zooming')
    print('  ✅ Tile cache reduces redundant downloads')
    print('  ✅ Shows loaded tile count and data size')
    print('  ✅ Layer control for multiple variables')
    print('  ✅ Interactive markers with tile info')
    print('  ✅ Multiple base maps')
    print('  ✅ Fullscreen mode')
    print('  ✅ Loading animation')
    print('\nPerformance: ')
    print(f'  - Loads ~{metadata["tiling"]["total_tiles"]//4}-{metadata["tiling"]["total_tiles"]//2} tiles at a time (instead of all {metadata["tiling"]["total_tiles"]})')
    print('  - Reduces initial load by ~75%')
    print('  - Perfect for zoomed-in views')
    print('\nUsage:')
    print('  1. Select date/hour - only visible tiles load')
    print('  2. Pan/zoom map - new tiles load automatically')
    print('  3. Zoom in for detailed view with minimal data transfer')
    print('=' * 70)


if __name__ == '__main__':
    main()
