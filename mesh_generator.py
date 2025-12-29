"""
Mesh Generation and Domain Handling for REMO Climate Data

This module provides utilities for generating regular meshes over geographic
regions and handling coordinate transformations between rotated and standard
coordinate systems.

Key Features:
    - Generate regular meshes over arbitrary regions
    - Domain boundary detection and filtering
    - Coordinate transformation (rotated ↔ geographic)
    - Weather station point integration
    - Germany-specific mesh utilities

Example:
    >>> from mesh_generator import MeshGenerator, GermanyDomain
    >>> 
    >>> # Generate mesh over Germany
    >>> domain = GermanyDomain()
    >>> mesh_gen = MeshGenerator(domain)
    >>> mesh = mesh_gen.generate_mesh(resolution=0.1)
    >>> print(f"Generated {len(mesh)} mesh points")
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
import xarray as xr


@dataclass
class Domain:
    """
    Geographic domain definition.
    
    Attributes:
        name: Domain name
        lat_min: Minimum latitude
        lat_max: Maximum latitude
        lon_min: Minimum longitude
        lon_max: Maximum longitude
        rlat_min: Minimum rotated latitude (optional)
        rlat_max: Maximum rotated latitude (optional)
        rlon_min: Minimum rotated longitude (optional)
        rlon_max: Maximum rotated longitude (optional)
    """
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    rlat_min: Optional[float] = None
    rlat_max: Optional[float] = None
    rlon_min: Optional[float] = None
    rlon_max: Optional[float] = None
    
    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if point is within domain bounds."""
        return (
            self.lat_min <= lat <= self.lat_max and
            self.lon_min <= lon <= self.lon_max
        )
    
    def get_center(self) -> Tuple[float, float]:
        """Get domain center coordinates."""
        lat_center = (self.lat_min + self.lat_max) / 2
        lon_center = (self.lon_min + self.lon_max) / 2
        return lat_center, lon_center
    
    def get_bounds(self) -> Dict[str, float]:
        """Get domain bounds as dictionary."""
        return {
            'lat_min': self.lat_min,
            'lat_max': self.lat_max,
            'lon_min': self.lon_min,
            'lon_max': self.lon_max
        }


class GermanyDomain(Domain):
    """Pre-defined domain for Germany."""
    
    def __init__(self):
        """Initialize Germany domain with standard boundaries."""
        super().__init__(
            name='Germany',
            lat_min=47.3,
            lat_max=55.5,
            lon_min=5.5,
            lon_max=16.0
        )


class MeshGenerator:
    """
    Generate regular meshes over geographic domains.
    
    This class creates regular grids of points over specified geographic
    regions for interpolation purposes.
    """
    
    def __init__(self, domain: Domain):
        """
        Initialize mesh generator.
        
        Args:
            domain: Domain definition for mesh generation
        """
        self.domain = domain
    
    def generate_mesh(
        self,
        resolution: float = 0.1,
        method: str = 'regular'
    ) -> pd.DataFrame:
        """
        Generate mesh points over domain.
        
        Args:
            resolution: Grid spacing in degrees (default: 0.1)
            method: Mesh generation method ('regular' or 'random')
        
        Returns:
            DataFrame with columns ['lat', 'lon', 'point_id']
        """
        if method == 'regular':
            return self._generate_regular_mesh(resolution)
        elif method == 'random':
            # Random sampling for testing
            n_points = int(
                (self.domain.lat_max - self.domain.lat_min) *
                (self.domain.lon_max - self.domain.lon_min) /
                (resolution ** 2)
            )
            return self._generate_random_mesh(n_points)
        else:
            raise ValueError(f"Unknown mesh method: {method}")
    
    def _generate_regular_mesh(self, resolution: float) -> pd.DataFrame:
        """Generate regular grid mesh."""
        # Create latitude and longitude arrays
        lats = np.arange(
            self.domain.lat_min,
            self.domain.lat_max + resolution,
            resolution
        )
        lons = np.arange(
            self.domain.lon_min,
            self.domain.lon_max + resolution,
            resolution
        )
        
        # Create mesh grid
        lon_mesh, lat_mesh = np.meshgrid(lons, lats)
        
        # Flatten to points
        mesh_points = pd.DataFrame({
            'lat': lat_mesh.flatten(),
            'lon': lon_mesh.flatten(),
            'point_id': range(len(lat_mesh.flatten()))
        })
        
        return mesh_points
    
    def _generate_random_mesh(self, n_points: int) -> pd.DataFrame:
        """Generate random mesh points."""
        lats = np.random.uniform(
            self.domain.lat_min,
            self.domain.lat_max,
            n_points
        )
        lons = np.random.uniform(
            self.domain.lon_min,
            self.domain.lon_max,
            n_points
        )
        
        return pd.DataFrame({
            'lat': lats,
            'lon': lons,
            'point_id': range(n_points)
        })
    
    def filter_mesh_by_domain(
        self,
        mesh: pd.DataFrame,
        domain: Optional[Domain] = None
    ) -> pd.DataFrame:
        """
        Filter mesh points to those within domain.
        
        Args:
            mesh: DataFrame with 'lat' and 'lon' columns
            domain: Domain to filter by (default: self.domain)
        
        Returns:
            Filtered DataFrame
        """
        if domain is None:
            domain = self.domain
        
        mask = (
            (mesh['lat'] >= domain.lat_min) &
            (mesh['lat'] <= domain.lat_max) &
            (mesh['lon'] >= domain.lon_min) &
            (mesh['lon'] <= domain.lon_max)
        )
        
        return mesh[mask].copy()
    
    def add_buffer_zone(
        self,
        mesh: pd.DataFrame,
        buffer_degrees: float = 0.5
    ) -> pd.DataFrame:
        """
        Add buffer zone around mesh for edge handling.
        
        Args:
            mesh: Original mesh DataFrame
            buffer_degrees: Buffer size in degrees
        
        Returns:
            Extended mesh DataFrame with buffer points
        """
        # Create extended domain
        extended_domain = Domain(
            name=f"{self.domain.name}_buffered",
            lat_min=self.domain.lat_min - buffer_degrees,
            lat_max=self.domain.lat_max + buffer_degrees,
            lon_min=self.domain.lon_min - buffer_degrees,
            lon_max=self.domain.lon_max + buffer_degrees
        )
        
        # Generate buffer mesh with same resolution as original
        # Estimate resolution from mesh
        if len(mesh) > 1:
            lat_diffs = np.diff(np.sort(mesh['lat'].unique()))
            resolution = np.median(lat_diffs[lat_diffs > 0])
        else:
            resolution = 0.1
        
        buffer_gen = MeshGenerator(extended_domain)
        buffer_mesh = buffer_gen.generate_mesh(resolution=resolution)
        
        # Mark original vs buffer points
        mesh = mesh.copy()
        mesh['is_buffer'] = False
        buffer_mesh['is_buffer'] = True
        
        # Combine (remove duplicates)
        combined = pd.concat([mesh, buffer_mesh], ignore_index=True)
        combined = combined.drop_duplicates(subset=['lat', 'lon'], keep='first')
        combined['point_id'] = range(len(combined))
        
        return combined


class CoordinateTransformer:
    """
    Transform between rotated and geographic coordinates.
    
    REMO uses a rotated pole coordinate system. This class provides
    transformations between rotated (rlat, rlon) and geographic (lat, lon)
    coordinates.
    
    Note:
        For REMO EUR-44, the transformation requires the pole position
        which is stored in the 'rotated_pole' variable of the NetCDF file.
    """
    
    def __init__(
        self,
        pole_lat: float,
        pole_lon: float
    ):
        """
        Initialize coordinate transformer.
        
        Args:
            pole_lat: North pole latitude in rotated system
            pole_lon: North pole longitude in rotated system
        """
        self.pole_lat = pole_lat
        self.pole_lon = pole_lon
    
    @classmethod
    def from_dataset(cls, dataset: xr.Dataset) -> 'CoordinateTransformer':
        """
        Create transformer from REMO dataset.
        
        Args:
            dataset: REMO xarray Dataset
        
        Returns:
            CoordinateTransformer instance
        """
        if 'rotated_pole' in dataset.data_vars or 'rotated_pole' in dataset.coords:
            rotated_pole = dataset['rotated_pole']
            pole_lat = float(rotated_pole.attrs.get('grid_north_pole_latitude', 39.25))
            pole_lon = float(rotated_pole.attrs.get('grid_north_pole_longitude', -162.0))
        else:
            # Default REMO EUR-44 pole position
            pole_lat = 39.25
            pole_lon = -162.0
        
        return cls(pole_lat, pole_lon)
    
    def rotated_to_geographic(
        self,
        rlat: np.ndarray,
        rlon: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert rotated coordinates to geographic.
        
        Args:
            rlat: Rotated latitude (degrees)
            rlon: Rotated longitude (degrees)
        
        Returns:
            Tuple of (lat, lon) in geographic coordinates
        
        Note:
            This is a simplified transformation. For production use,
            consider using more accurate transformations from pyproj
            or cartopy.
        """
        # Simple approximation for small regions
        # For accurate transformation, use proper rotation matrices
        
        # Convert to radians
        rlat_rad = np.deg2rad(rlat)
        rlon_rad = np.deg2rad(rlon)
        pole_lat_rad = np.deg2rad(self.pole_lat)
        pole_lon_rad = np.deg2rad(self.pole_lon)
        
        # Simplified rotation (for demonstration)
        # In practice, use proper spherical coordinate rotation
        lat = np.rad2deg(np.arcsin(
            np.sin(rlat_rad) * np.sin(pole_lat_rad) +
            np.cos(rlat_rad) * np.cos(pole_lat_rad) * np.cos(rlon_rad)
        ))
        
        lon = pole_lon + np.rad2deg(np.arctan2(
            np.cos(rlat_rad) * np.sin(rlon_rad),
            np.cos(rlat_rad) * np.cos(rlon_rad) * np.sin(pole_lat_rad) -
            np.sin(rlat_rad) * np.cos(pole_lat_rad)
        ))
        
        return lat, lon
    
    def geographic_to_rotated(
        self,
        lat: np.ndarray,
        lon: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert geographic coordinates to rotated.
        
        Args:
            lat: Geographic latitude (degrees)
            lon: Geographic longitude (degrees)
        
        Returns:
            Tuple of (rlat, rlon) in rotated coordinates
        """
        # Inverse transformation
        # This is also simplified; use proper transformation in production
        
        lat_rad = np.deg2rad(lat)
        lon_rad = np.deg2rad(lon)
        pole_lat_rad = np.deg2rad(self.pole_lat)
        pole_lon_rad = np.deg2rad(self.pole_lon)
        
        dlon = lon_rad - pole_lon_rad
        
        rlat = np.rad2deg(np.arcsin(
            np.sin(lat_rad) * np.sin(pole_lat_rad) +
            np.cos(lat_rad) * np.cos(pole_lat_rad) * np.cos(dlon)
        ))
        
        rlon = np.rad2deg(np.arctan2(
            np.cos(lat_rad) * np.sin(dlon),
            np.cos(lat_rad) * np.cos(dlon) * np.sin(pole_lat_rad) -
            np.sin(lat_rad) * np.cos(pole_lat_rad)
        ))
        
        return rlat, rlon


class WeatherStationManager:
    """
    Manage weather station points for interpolation validation.
    
    This class handles synthetic and real weather station data
    for use in interpolation and validation.
    """
    
    def __init__(self):
        """Initialize weather station manager."""
        self.stations = pd.DataFrame(columns=['name', 'lat', 'lon', 'elevation'])
    
    def add_station(
        self,
        name: str,
        lat: float,
        lon: float,
        elevation: Optional[float] = None
    ):
        """
        Add a weather station.
        
        Args:
            name: Station name
            lat: Latitude
            lon: Longitude
            elevation: Elevation in meters (optional)
        """
        new_station = pd.DataFrame([{
            'name': name,
            'lat': lat,
            'lon': lon,
            'elevation': elevation if elevation is not None else 0.0
        }])
        self.stations = pd.concat([self.stations, new_station], ignore_index=True)
    
    def generate_synthetic_stations(
        self,
        domain: Domain,
        n_stations: int = 10,
        seed: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Generate synthetic weather stations within domain.
        
        Args:
            domain: Domain for station generation
            n_stations: Number of stations to generate
            seed: Random seed for reproducibility
        
        Returns:
            DataFrame with synthetic station locations
        """
        if seed is not None:
            np.random.seed(seed)
        
        lats = np.random.uniform(domain.lat_min, domain.lat_max, n_stations)
        lons = np.random.uniform(domain.lon_min, domain.lon_max, n_stations)
        elevations = np.random.uniform(0, 500, n_stations)  # Random elevations
        
        stations = pd.DataFrame({
            'name': [f'Station_{i+1}' for i in range(n_stations)],
            'lat': lats,
            'lon': lons,
            'elevation': elevations
        })
        
        self.stations = pd.concat([self.stations, stations], ignore_index=True)
        return stations
    
    def get_german_reference_stations(self) -> pd.DataFrame:
        """
        Get a few reference weather stations in Germany.
        
        Returns:
            DataFrame with German weather station locations
        """
        # Some well-known German weather stations (approximate coordinates)
        stations = pd.DataFrame([
            {'name': 'Berlin-Tempelhof', 'lat': 52.47, 'lon': 13.40, 'elevation': 48},
            {'name': 'München-Stadt', 'lat': 48.13, 'lon': 11.57, 'elevation': 519},
            {'name': 'Hamburg-Fuhlsbüttel', 'lat': 53.63, 'lon': 9.98, 'elevation': 11},
            {'name': 'Frankfurt-Flughafen', 'lat': 50.03, 'lon': 8.58, 'elevation': 112},
            {'name': 'Köln-Bonn', 'lat': 50.86, 'lon': 7.14, 'elevation': 92},
            {'name': 'Stuttgart-Echterdingen', 'lat': 48.68, 'lon': 9.22, 'elevation': 371},
        ])
        
        self.stations = pd.concat([self.stations, stations], ignore_index=True)
        return stations
    
    def to_dataframe(self) -> pd.DataFrame:
        """Get all stations as DataFrame."""
        return self.stations.copy()
    
    def filter_by_domain(self, domain: Domain) -> pd.DataFrame:
        """
        Filter stations within domain.
        
        Args:
            domain: Domain to filter by
        
        Returns:
            Filtered DataFrame
        """
        mask = (
            (self.stations['lat'] >= domain.lat_min) &
            (self.stations['lat'] <= domain.lat_max) &
            (self.stations['lon'] >= domain.lon_min) &
            (self.stations['lon'] <= domain.lon_max)
        )
        return self.stations[mask].copy()


def extract_remo_grid_in_domain(
    dataset: xr.Dataset,
    domain: Domain,
    use_phi_rla: bool = True
) -> pd.DataFrame:
    """
    Extract REMO grid points within a geographic domain.
    
    Args:
        dataset: REMO xarray Dataset
        domain: Domain to extract points from
        use_phi_rla: If True, use PHI/RLA variables for lat/lon
                     If False, use rotated coordinates directly
    
    Returns:
        DataFrame with grid point coordinates and indices
    """
    if use_phi_rla and 'PHI' in dataset.data_vars and 'RLA' in dataset.data_vars:
        # Use actual lat/lon from PHI/RLA
        phi = dataset['PHI'].isel(time=0)  # Latitude
        rla = dataset['RLA'].isel(time=0)  # Longitude
        
        points = []
        for iy in range(len(dataset.rlat)):
            for ix in range(len(dataset.rlon)):
                lat = float(phi.isel(rlat=iy, rlon=ix).values)
                lon = float(rla.isel(rlat=iy, rlon=ix).values)
                
                if domain.contains_point(lat, lon):
                    points.append({
                        'rlat_idx': iy,
                        'rlon_idx': ix,
                        'rlat': float(dataset.rlat[iy].values),
                        'rlon': float(dataset.rlon[ix].values),
                        'lat': lat,
                        'lon': lon
                    })
        
        return pd.DataFrame(points)
    
    else:
        # Use rotated coordinates and approximate transformation
        transformer = CoordinateTransformer.from_dataset(dataset)
        
        points = []
        for iy, rlat in enumerate(dataset.rlat.values):
            for ix, rlon in enumerate(dataset.rlon.values):
                lat, lon = transformer.rotated_to_geographic(
                    np.array([rlat]),
                    np.array([rlon])
                )
                lat, lon = float(lat[0]), float(lon[0])
                
                if domain.contains_point(lat, lon):
                    points.append({
                        'rlat_idx': iy,
                        'rlon_idx': ix,
                        'rlat': rlat,
                        'rlon': rlon,
                        'lat': lat,
                        'lon': lon
                    })
        
        return pd.DataFrame(points)
