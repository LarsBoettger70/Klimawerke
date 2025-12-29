import xarray as xr
import pandas as pd

NETCDF_FILE = "remo_germany_subset.nc"

ds = xr.open_dataset(NETCDF_FILE)

print("\n=== DATASET INFO ===")
print(ds)

print("\n=== DIMENSIONS ===")
print(ds.dims)

print("\n=== DATA VARIABLES ===")
print(list(ds.data_vars))

print("\n=== COORDS ===")
print(ds.coords)

# Hilfsfunktion: sicher einen Skalar holen, falls möglich
def get_scalar(var, indexers):
    try:
        da = ds[var].isel(**indexers)
        if da.size != 1:
            return None
        return float(da.values.reshape(-1)[0])
    except Exception:
        return None

# Deutschland-Bereich in realen geografischen Koordinaten (lat/lon)
DE_MIN_LAT, DE_MAX_LAT = 47.3, 55.5   # Breite
DE_MIN_LON, DE_MAX_LON = 5.5, 16.0    # Länge

print("\n=== SAMPLE GRID POINTS IN GERMANY (first 20) ===")

n_lat = ds.sizes["rlat"]
n_lon = ds.sizes["rlon"]

rows = []

for iy in range(n_lat):
    for ix in range(n_lon):
        # reale Geokoordinaten aus PHI/RLA
        lat_val = get_scalar("PHI", {"time": 0, "rlat": iy, "rlon": ix})
        lon_val = get_scalar("RLA", {"time": 0, "rlat": iy, "rlon": ix})

        if lat_val is None or lon_val is None:
            continue

        # Filter auf Deutschland
        if not (DE_MIN_LAT <= lat_val <= DE_MAX_LAT and DE_MIN_LON <= lon_val <= DE_MAX_LON):
            continue

        row = {
            "gridy": iy,
            "gridx": ix,
            "lat": lat_val,
            "lon": lon_val,
        }

        # 2D-Felder TS, RLA, WS, ACLC (auf rlat/rlon)
        if "TS" in ds.data_vars:
            row["TS"] = get_scalar("TS", {"time": 0, "rlat": iy, "rlon": ix})
        if "RLA" in ds.data_vars:
            row["RLA_Wm2"] = get_scalar("RLA", {"time": 0, "rlat": iy, "rlon": ix})
        if "WS" in ds.data_vars:
            row["WS_ms"] = get_scalar("WS", {"time": 0, "rlat": iy, "rlon": ix})

        # 3D-Felder mit lev, rlon_2 (unterstes Level)
        if "T" in ds.data_vars:
            row["T_lev0"] = get_scalar("T", {"time": 0, "lev": 0, "rlat": iy, "rlon_2": ix})
        if "U" in ds.data_vars:
            row["U_lev0"] = get_scalar("U", {"time": 0, "lev": 0, "rlat": iy, "rlon_2": ix})
        if "V" in ds.data_vars:
            row["V_lev0"] = get_scalar("V", {"time": 0, "lev": 0, "rlat": iy, "rlon_2": ix})
        if "QW" in ds.data_vars:
            row["QW_lev0"] = get_scalar("QW", {"time": 0, "lev": 0, "rlat": iy, "rlon_2": ix})
        if "QI" in ds.data_vars:
            row["QI_lev0"] = get_scalar("QI", {"time": 0, "lev": 0, "rlat": iy, "rlon_2": ix})

        rows.append(row)

        # Nur die ersten 20 deutschen Punkte
        if len(rows) >= 20:
            break
    if len(rows) >= 20:
        break

df_sample = pd.DataFrame(rows)
print(df_sample.to_string(index=False))

