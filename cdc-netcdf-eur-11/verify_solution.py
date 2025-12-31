"""
Verification script to test the CDC visualization pipeline
"""

import os
import json
import sys

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✓ {description}: {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"✗ {description}: {filepath} NOT FOUND")
        return False

def verify_geojson_files():
    """Verify GeoJSON files were generated correctly"""
    print("\n=== Verifying GeoJSON Files ===")
    
    # Check if directory exists
    if not os.path.exists('geojson'):
        print("✗ geojson/ directory not found")
        return False
    
    # Check index file
    if not check_file_exists('geojson/timeseries_index.json', 'Timeseries index'):
        return False
    
    # Load and verify index
    with open('geojson/timeseries_index.json', 'r') as f:
        index = json.load(f)
    
    print(f"\n  Timestamps: {len(index['timestamps'])}")
    print(f"  Variables: {list(index['files'].keys())}")
    
    # Verify all referenced files exist
    missing_files = 0
    total_files = 0
    
    for var_name, filenames in index['files'].items():
        for filename in filenames:
            total_files += 1
            filepath = os.path.join('geojson', filename)
            if not os.path.exists(filepath):
                missing_files += 1
                print(f"  ✗ Missing: {filename}")
    
    if missing_files > 0:
        print(f"\n✗ {missing_files}/{total_files} files are missing")
        return False
    else:
        print(f"✓ All {total_files} GeoJSON files present")
        return True

def verify_html_map():
    """Verify HTML map was created"""
    print("\n=== Verifying HTML Map ===")
    
    if not check_file_exists('interactive_map_with_timeslider.html', 'Interactive map'):
        return False
    
    # Check file content
    with open('interactive_map_with_timeslider.html', 'r') as f:
        content = f.read()
    
    required_elements = [
        ('Folium map', 'folium-map'),
        ('Layer control', 'LayerControl'),
        ('Circle markers', 'CircleMarker'),
        ('Minimap', 'MiniMap'),
        ('Fullscreen', 'Fullscreen'),
    ]
    
    all_present = True
    for name, element in required_elements:
        if element in content:
            print(f"  ✓ {name} present")
        else:
            print(f"  ✗ {name} missing")
            all_present = False
    
    return all_present

def verify_scripts():
    """Verify the main scripts exist"""
    print("\n=== Verifying Scripts ===")
    
    scripts = [
        'A3_1_generate_geojson_from_netcdf.py',
        'A3_2_build_interactive_map_with_timeslider.py',
        'README.md'
    ]
    
    all_present = True
    for script in scripts:
        if not check_file_exists(script, f'Script'):
            all_present = False
    
    return all_present

def main():
    print("=" * 70)
    print("CDC European Weather/Wave Data Visualization - Verification")
    print("=" * 70)
    
    # Change to correct directory
    if os.path.exists('cdc-netcdf-eur-11'):
        os.chdir('cdc-netcdf-eur-11')
    
    results = []
    
    # Run verifications
    results.append(("Scripts", verify_scripts()))
    results.append(("GeoJSON Files", verify_geojson_files()))
    results.append(("HTML Map", verify_html_map()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✓ All verifications passed!")
        print("\nYou can now open 'interactive_map_with_timeslider.html' in a web browser.")
        return 0
    else:
        print("\n✗ Some verifications failed. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
