import xarray as xr
import pandas as pd

# List of available files
file_options = {
    "1": "data_stream-wave_stepType-instant.nc",  # First file
    "2": "data_stream-oper_stepType-instant.nc",  # Second file
    "3": "data_stream-oper_stepType-accum.nc",    # Third file
}

# Menu to select the file
print("Select a file to analyze:")
for key, filename in file_options.items():
    print(f"{key}: {filename}")

file_choice = input("\nPlease enter the number corresponding to your choice: ").strip()

if file_choice not in file_options:
    print("Invalid choice! Please restart the program and select a valid option.")
    exit()

# Load the selected NetCDF file
NETCDF_FILE = file_options[file_choice]
print(f"\nAnalyzing file: {NETCDF_FILE}")

ds = xr.open_dataset(NETCDF_FILE)

# Prepare the data structure output string
output = []

output.append("\n=== FILE OVERVIEW ===\n")
output.append(str(ds))

output.append("\n=== DIMENSIONS ===\n")
output.append(str(ds.dims))

output.append("\n=== COORDINATES ===\n")
output.append(str(ds.coords))

output.append("\n=== DATA VARIABLES ===\n")
output.append(str(list(ds.data_vars)))

# Dynamically use latitude and longitude dimensions
lat_coord = "latitude"
lon_coord = "longitude"

lat_values = ds[lat_coord].values
lon_values = ds[lon_coord].values

rows = []
max_points = 20  # Limit grid points to the first 20 for simplicity
output.append("\n=== SAMPLE GRID POINTS (first 20) ===\n")

for i in range(min(max_points, len(lat_values) * len(lon_values))):
    iy = i // len(lon_values)  # Grid index in latitude
    ix = i % len(lon_values)  # Grid index in longitude

    row = {
        "gridy": iy,
        "gridx": ix,
        "latitude": float(lat_values[iy]),
        "longitude": float(lon_values[ix]),
    }

    # Dynamically extract variables for the grid point
    for var in ds.data_vars:
        try:
            value = ds[var].isel(valid_time=0, latitude=iy, longitude=ix).values
            row[var] = float(value) if value.size > 0 else None
        except Exception:
            row[var] = None  # Handle missing values gracefully

    rows.append(row)

# Create a DataFrame for the grid points
df_sample = pd.DataFrame(rows)
output.append(df_sample.to_string(index=False))

# Save the output to a text file
base_name = NETCDF_FILE[:-3]  # Remove the last three characters (".nc")
text_filename = f"datastructure_{base_name}.txt"

with open(text_filename, "w") as file:
    file.write("\n".join(output))

# Notify the user
print("\n")  # An empty line for better readability
print(f"Data structure saved to '{text_filename}'.")
print("\n=== SAMPLE GRID POINTS (first 20) ===")
print(df_sample.to_string(index=False))
