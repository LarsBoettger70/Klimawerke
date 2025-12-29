#!/usr/bin/env python3
'''
Scatter-Diagramm: lon (x) vs. lat (y) mit Temperatur aus climate_parameters.csv
Ausgabe als HTML-Datei (PNG eingebettet).
'''

import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

INPUT_CSV = 'climate_parameters.csv'
OUTPUT_HTML = 'lon_lat_temperature_scatter.html'

def main():
    print(f'Lade {INPUT_CSV}...')
    df = pd.read_csv(INPUT_CSV)

    if 'TS_C' not in df.columns:
        raise ValueError("Spalte 'TS_C' nicht im CSV gefunden.")

    df_plot = df.dropna(subset=['TS_C', 'lat', 'lon']).copy()
    df_plot = df_plot.query(
        'lat >= 47.3 and lat <= 55.5 and lon >= 5.5 and lon <= 16.0'
    )

    print(f'{len(df_plot)} Punkte im Plot.')

    fig, ax = plt.subplots(figsize=(9, 7))
    sc = ax.scatter(
        df_plot['lon'],
        df_plot['lat'],
        c=df_plot['TS_C'],
        cmap='viridis',
        s=15
    )
    ax.set_xlabel('Longitude (°)')
    ax.set_ylabel('Latitude (°)')
    ax.set_title('REMO Grid Points – Surface Temperature over Germany')
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('Surface Temperature (°C)')

    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('ascii')

    html = f"""
<html>
<head>
<meta charset="utf-8">
<title>REMO lon/lat Temperature Scatter</title>
</head>
<body>
<h1>REMO Grid Points – Surface Temperature over Germany</h1>
<p>Scatter-Diagramm der Gridpunkte (lon/lat) mit Oberflächentemperatur (°C) als Farbskala.</p>
<img src="data:image/png;base64,{img_base64}" alt="lon/lat temperature scatter">
</body>
</html>
"""
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)

    print(f'Diagramm als HTML gespeichert: {OUTPUT_HTML}')


if __name__ == '__main__':
    main()
