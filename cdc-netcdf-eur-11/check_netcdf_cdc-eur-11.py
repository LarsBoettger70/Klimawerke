# check netcdf dateien auf datenfelder

import xarray as xr
import pandas as pd

NETCDF_FILE = "data_stream-oper_stepType-accum.nc"
# data_stream-oper_stepType-accum.nc
# data_stream-oper_stepType-instant.nc
# data_stream-oper_stepType-accum.nc

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
        # Wenn noch mehr als 0 Dimensionen übrig sind, nicht erzwingen
        if da.size != 1:
            return None
        return float(da.values.reshape(-1)[0])
    except Exception:
        return None

# Erste 20 Zeilen ausgewählter Felder anzeigen
print("\n=== SAMPLE GRID POINTS (first 20) ===")

rlat = ds.rlat.values
rlon = ds.rlon.values
n_lon = len(rlon)

rows = []
for i in range(20):
    iy = i // n_lon
    ix = i % n_lon

    row = {
        "gridy": iy,
        "gridx": ix,
        "rlat": float(rlat[iy]),
        "rlon": float(rlon[ix]),
    }

    # 2D-Felder TS, RLA, WS, ACLC (evtl. mit zusätzlicher Tiefe)
    if "TS" in ds.data_vars:
        row["TS"] = get_scalar("TS", {"time": 0, "rlat": iy, "rlon": ix})
    if "RLA" in ds.data_vars:
        row["RLA"] = get_scalar("RLA", {"time": 0, "rlat": iy, "rlon": ix})
    if "WS" in ds.data_vars:
        row["WS"] = get_scalar("WS", {"time": 0, "rlat": iy, "rlon": ix})
    if "ACLC" in ds.data_vars:
        row["ACLC"] = get_scalar("ACLC", {"time": 0, "rlat": iy, "rlon": ix})

    # 3D-Felder mit lev, rlon_2
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

df_sample = pd.DataFrame(rows)
print(df_sample.to_string(index=False))
