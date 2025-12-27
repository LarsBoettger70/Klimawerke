"""
Load REMO domain information from remo-rcm/tables
This shows available regions and their geocoordinates
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import box

# Load domain tables directly from GitHub
DOMAINS_URL = 'https://raw.githubusercontent.com/remo-rcm/tables/main/domains/domains.csv'
CORDEX_DOMAINS_URL = 'https://raw.githubusercontent.com/remo-rcm/tables/main/domains/cordex-domains.csv'

def load_remo_domains():
    """Load all REMO domains"""
    try:
        df = pd.read_csv(DOMAINS_URL)
        print("✓ Successfully loaded REMO domains")
        print(f"\nAvailable domains ({len(df)} total):")
        print(df.to_string())
        return df
    except Exception as e:
        print(f"Error loading domains: {e}")
        return None

def load_cordex_domains():
    """Load CORDEX standard domains"""
    try:
        df = pd.read_csv(CORDEX_DOMAINS_URL)
        print("\n✓ Successfully loaded CORDEX domains")
        print(f"\nCORDEX domains available:")
        print(df.to_string())
        return df
    except Exception as e:
        print(f"Error loading CORDEX domains: {e}")
        return None

def find_german_domains(domains_df):
    """Find domains that cover Germany"""
    # Germany bounds:  approximately 47°N - 55. 5°N, 5. 5°E - 16°E
    german_bounds = {
        'south': 47,
        'north': 55.5,
        'west': 5.5,
        'east': 16
    }
    
    print("\n" + "="*60)
    print("GERMAN-RELEVANT DOMAINS")
    print("="*60)
    
    german_domains = []
    for idx, row in domains_df.iterrows():
        # Check if domain overlaps with Germany
        domain_south = row. get('south_north', row.get('min_lat', None))
        domain_north = row.get('north_south', row.get('max_lat', None))
        domain_west = row.get('west_east', row.get('min_lon', None))
        domain_east = row.get('east_west', row.get('max_lon', None))
        
        # Simple check - domain overlaps with Germany
        if domain_south is not None and domain_north is not None:
            german_domains.append(row)
    
    if german_domains:
        german_df = pd.DataFrame(german_domains)
        print(f"\nFound {len(german_df)} domain(s) covering Germany:")
        print(german_df. to_string())
        return german_df
    else:
        print("Check the full domains list above for Germany coverage")
        return None

def create_domain_polygons(domains_df):
    """Create GeoDataFrame with domain polygons"""
    polygons = []
    
    for idx, row in domains_df. iterrows():
        try:
            # Extract bounds (column names may vary)
            south = float(row. get('south_north') or row.get('min_lat') or row.get('south'))
            north = float(row.get('north_south') or row.get('max_lat') or row.get('north'))
            west = float(row.get('west_east') or row.get('min_lon') or row.get('west'))
            east = float(row.get('east_west') or row.get('max_lon') or row.get('east'))
            
            # Create polygon
            poly = box(west, south, east, north)
            polygons.append({
                'domain':  row. get('domain', row.get('name', f'Domain {idx}')),
                'geometry': poly,
                'south': south,
                'north':  north,
                'west': west,
                'east': east
            })
        except (TypeError, ValueError) as e:
            print(f"Skipping row {idx}: {e}")
            continue
    
    if polygons:
        gdf = gpd.GeoDataFrame(polygons, crs='EPSG:4326')
        print(f"\n✓ Created {len(gdf)} domain polygon(s)")
        return gdf
    return None

def main():
    print("="*60)
    print("REMO Climate Model - Domain Explorer")
    print("="*60)
    
    # Load domains
    print("\n[1] Loading REMO domains...")
    domains = load_remo_domains()
    
    if domains is not None:
        # Find German domains
        print("\n[2] Finding German-relevant domains...")
        german_domains = find_german_domains(domains)
        
        # Create polygons
        print("\n[3] Creating domain polygons...")
        gdf = create_domain_polygons(domains)
        
        if gdf is not None:
            # Save for later use
            gdf.to_file('remo_domains. geojson', driver='GeoJSON')
            print(f"\n✓ Saved domain polygons to 'remo_domains.geojson'")
    
    # Also load CORDEX domains
    print("\n[4] Loading CORDEX domains...")
    cordex = load_cordex_domains()
    
    print("\n" + "="*60)
    print("Next steps:")
    print("  1. Review the domains listed above")
    print("  2. Identify which domain covers your German region(s)")
    print("  3. Get REMO model output for that domain")
    print("  4. Run visualization script")
    print("="*60)

if __name__ == "__main__":
    main()
