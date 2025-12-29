import hashlib
import re
import sys
from pathlib import Path

import requests

# Name des von ESGF erzeugten wget-Skripts
WGET_SCRIPT = Path("wget_script_eur-22-gerics-2025-12-27_17-20-54.sh")

# Zielverzeichnis für alle NetCDF-Dateien
BASE_DIR = Path("gerics_data")
BASE_DIR.mkdir(exist_ok=True)


def sha256_file(path: Path) -> str:
    """Berechne SHA256-Checksumme einer Datei."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_file_list(script_path: Path):
    """
    Sucht in der wget-Skriptdatei nach Mustern:
    'filename' 'url' 'SHA256' 'checksum'
    und liefert eine Liste von Tupeln (filename, url, checksum).
    """
    entries = []
    # Beispielzeile:
    # 'file.nc' 'http://...' 'SHA256' 'abcdef1234...'
    pattern = re.compile(
        r"'([^']+)'\s+'([^']+)'\s+'SHA256'\s+'([0-9a-fA-F]{64})'"
    )

    with script_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            m = pattern.search(line)
            if m:
                filename, url, checksum = m.groups()
                entries.append((filename, url, checksum.lower()))
    return entries

def download_file(url: str, target: Path, chunk_size: int = 1024 * 1024):
    """Lädt eine Datei mit Streaming-Download."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)


def main():
    if not WGET_SCRIPT.exists():
        print(f"wget-Script nicht gefunden: {WGET_SCRIPT}")
        sys.exit(1)

    entries = parse_file_list(WGET_SCRIPT)
    print(f"{len(entries)} Dateien im Script gefunden.")

    for i, (filename, url, checksum) in enumerate(entries, start=1):
        target = BASE_DIR / filename
        print(f"\n[{i}/{len(entries)}] {filename}")

        # Schon vorhandene Datei mit korrekter Checksumme überspringen
        if target.exists():
            try:
                local = sha256_file(target)
            except Exception as e:
                print(f"  Fehler beim Checksum lesen: {e}, lade neu.")
                target.unlink(missing_ok=True)
            else:
                if local == checksum:
                    print("  Schon vorhanden (SHA256 ok).")
                    continue
                else:
                    print("  Datei existiert, aber SHA256 falsch – lade neu.")
                    target.unlink()

        print(f"  Lade von {url}")
        try:
            download_file(url, target)
        except Exception as e:
            print(f"  Fehler beim Download: {e}")
            continue

        # Prüfen
        try:
            local = sha256_file(target)
        except Exception as e:
            print(f"  Fehler beim SHA256-Berechnen: {e}")
            target.unlink(missing_ok=True)
            continue

        if local == checksum:
            print("  SHA256 ok.")
        else:
            print("  SHA256 FEHLER, Datei wird gelöscht.")
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
