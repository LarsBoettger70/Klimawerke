"""
Polynomial Interpolation Module for REMO Climate Model Data

This module provides 2D polynomial interpolation capabilities for downscaling
REMO climate model data from coarse grids (EUR-44, EUR-22, EUR-11) to regional
and point-level resolution.

Mathematical Approach:
    - Uses Radial Basis Function (RBF) interpolation for smooth surfaces
    - Supports multiple kernel types (thin_plate_spline, multiquadric, cubic)
    - Handles irregular grid spacing in rotated coordinate systems
    - Gracefully manages missing/NaN values through masking
    
The interpolation creates smooth "arcs" around climate model grid points
rather than linear connections, providing more realistic transitions between
coarse grid cells.

Example:
    >>> from polynomial_interpolation import RemoInterpolator
    >>> import xarray as xr
    >>> 
    >>> # Load REMO data
    >>> ds = xr.open_dataset('remo_EUR-44.nc')
    >>> 
    >>> # Create interpolator for temperature
    >>> interp = RemoInterpolator(ds, variable='TS', time_idx=0)
    >>> 
    >>> # Interpolate at specific points
    >>> values = interp.interpolate(query_rlat=[0.5, 1.0], query_rlon=[5.0, 5.5])
"""

import numpy as np
import xarray as xr
from scipy.interpolate import RBFInterpolator, griddata
from scipy.spatial import cKDTree
from typing import Tuple, Optional, Union, List
import warnings


class RemoInterpolator:
    """
    2D Polynomial/RBF Interpolator for REMO climate data.
    
    This class handles interpolation from coarse REMO grid points to arbitrary
    query locations using smooth polynomial or radial basis function methods.
    
    Attributes:
        dataset (xr.Dataset): REMO dataset
        variable (str): Climate variable to interpolate (e.g., 'TS', 'T')
        time_idx (int): Time index to use for interpolation
        kernel (str): RBF kernel type ('thin_plate_spline', 'cubic', etc.)
        neighbors (int): Number of neighbors to use for local interpolation
    """
    
    def __init__(
        self,
        dataset: xr.Dataset,
        variable: str,
        time_idx: int = 0,
        lev_idx: Optional[int] = None,
        kernel: str = 'thin_plate_spline',
        neighbors: int = 16,
        smoothing: float = 0.0
    ):
        """
        Initialize the REMO interpolator.
        
        Args:
            dataset: xarray Dataset containing REMO data
            variable: Name of variable to interpolate (e.g., 'TS', 'T', 'TEMP2')
            time_idx: Time index to use (default: 0)
            lev_idx: Level index for 3D variables (default: None for 2D variables)
            kernel: RBF kernel type (default: 'thin_plate_spline')
            neighbors: Number of nearest neighbors for local interpolation (default: 16)
            smoothing: Smoothing parameter for RBF (default: 0.0 for exact interpolation)
        
        Raises:
            ValueError: If variable not found in dataset
            ValueError: If coordinate system not supported
        """
        self.dataset = dataset
        self.variable = variable
        self.time_idx = time_idx
        self.lev_idx = lev_idx
        self.kernel = kernel
        self.neighbors = neighbors
        self.smoothing = smoothing
        
        # Validate variable exists
        if variable not in dataset.data_vars:
            raise ValueError(
                f"Variable '{variable}' not found in dataset. "
                f"Available: {list(dataset.data_vars)}"
            )
        
        # Validate coordinate system
        if 'rlon' not in dataset.coords or 'rlat' not in dataset.coords:
            raise ValueError(
                "Dataset must have 'rlon' and 'rlat' coordinates. "
                f"Found: {list(dataset.coords)}"
            )
        
        # Extract grid data
        self._extract_grid_data()
        
        # Build KD-tree for neighbor search
        self._build_kdtree()
        
        # Interpolator will be created on-demand
        self._interpolator = None
    
    def _extract_grid_data(self):
        """Extract grid coordinates and values from dataset."""
        # Get variable data
        var_data = self.dataset[self.variable]
        
        # Select time slice
        if 'time' in var_data.dims:
            var_data = var_data.isel(time=self.time_idx)
        
        # Select level if applicable
        if self.lev_idx is not None and 'lev' in var_data.dims:
            var_data = var_data.isel(lev=self.lev_idx)
        
        # Get coordinate grids
        rlon = self.dataset.rlon.values
        rlat = self.dataset.rlat.values
        
        # Create 2D mesh
        self.rlon_grid, self.rlat_grid = np.meshgrid(rlon, rlat)
        
        # Flatten for interpolation
        self.rlon_flat = self.rlon_grid.flatten()
        self.rlat_flat = self.rlat_grid.flatten()
        
        # Get values
        if len(var_data.shape) == 2:
            # Expected: (rlat, rlon)
            self.values_flat = var_data.values.flatten()
        else:
            raise ValueError(
                f"Unexpected data shape for {self.variable}: {var_data.shape}. "
                f"Expected 2D array after time/level selection."
            )
        
        # Create mask for valid (non-NaN) values
        self.valid_mask = ~np.isnan(self.values_flat)
        
        # Filter to valid points
        self.rlon_valid = self.rlon_flat[self.valid_mask]
        self.rlat_valid = self.rlat_flat[self.valid_mask]
        self.values_valid = self.values_flat[self.valid_mask]
        
        # Stack coordinates for KD-tree and interpolation
        self.points_valid = np.column_stack([self.rlat_valid, self.rlon_valid])
    
    def _build_kdtree(self):
        """Build KD-tree for efficient nearest neighbor search."""
        if len(self.points_valid) > 0:
            self.kdtree = cKDTree(self.points_valid)
        else:
            self.kdtree = None
            warnings.warn("No valid data points found for interpolation.")
    
    def _build_interpolator(self, local_points: np.ndarray, local_values: np.ndarray):
        """
        Build RBF interpolator for local region.
        
        Args:
            local_points: Array of shape (N, 2) with [rlat, rlon] coordinates
            local_values: Array of shape (N,) with data values
        
        Returns:
            RBFInterpolator instance
        """
        return RBFInterpolator(
            local_points,
            local_values,
            kernel=self.kernel,
            smoothing=self.smoothing,
            epsilon=1.0
        )
    
    def find_neighbors(
        self,
        query_rlat: Union[float, np.ndarray],
        query_rlon: Union[float, np.ndarray],
        k: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find k nearest neighbors for query points.
        
        Args:
            query_rlat: Query latitude(s) in rotated coordinates
            query_rlon: Query longitude(s) in rotated coordinates
            k: Number of neighbors (default: self.neighbors)
        
        Returns:
            Tuple of (distances, indices) for nearest neighbors
        """
        if k is None:
            k = self.neighbors
        
        # Ensure arrays
        query_rlat = np.atleast_1d(query_rlat)
        query_rlon = np.atleast_1d(query_rlon)
        
        # Stack query points
        query_points = np.column_stack([query_rlat, query_rlon])
        
        # Query KD-tree
        if self.kdtree is None:
            raise ValueError("No valid data points available for neighbor search.")
        
        # Limit k to available points
        k = min(k, len(self.points_valid))
        
        distances, indices = self.kdtree.query(query_points, k=k)
        
        return distances, indices
    
    def interpolate(
        self,
        query_rlat: Union[float, np.ndarray],
        query_rlon: Union[float, np.ndarray],
        method: str = 'rbf'
    ) -> np.ndarray:
        """
        Interpolate variable at query points.
        
        This method creates smooth polynomial surfaces through nearby grid points
        and evaluates at the query locations. Supports both global and local
        interpolation strategies.
        
        Args:
            query_rlat: Query latitude(s) in rotated coordinates
            query_rlon: Query longitude(s) in rotated coordinates
            method: Interpolation method ('rbf' or 'linear' or 'cubic')
        
        Returns:
            Interpolated values at query points
        
        Raises:
            ValueError: If no valid data points available
        """
        # Ensure arrays
        query_rlat = np.atleast_1d(query_rlat)
        query_rlon = np.atleast_1d(query_rlon)
        
        if len(self.values_valid) == 0:
            raise ValueError("No valid data points available for interpolation.")
        
        # Stack query points
        query_points = np.column_stack([query_rlat, query_rlon])
        
        if method == 'rbf':
            # Local RBF interpolation using nearest neighbors
            interpolated = np.zeros(len(query_points))
            
            for i, qp in enumerate(query_points):
                # Find neighbors
                distances, indices = self.find_neighbors(qp[0], qp[1])
                
                # Get local points and values
                # Handle both single point and multiple points cases
                if np.isscalar(indices):
                    indices = np.array([indices])
                elif len(indices.shape) > 1:
                    # If 2D array (from single query), flatten
                    indices = indices.flatten()
                
                local_points = self.points_valid[indices]
                local_values = self.values_valid[indices]
                
                # Build local interpolator
                if len(local_points) >= 3:  # Need at least 3 points
                    try:
                        interp = self._build_interpolator(local_points, local_values)
                        interpolated[i] = interp(qp.reshape(1, -1))[0]
                    except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
                        # Fallback to nearest neighbor if RBF fails
                        interpolated[i] = local_values[0]
                else:
                    # Fallback to nearest neighbor
                    interpolated[i] = local_values[0]
            
            return interpolated
        
        elif method in ['linear', 'cubic']:
            # Use scipy's griddata for linear/cubic interpolation
            interpolated = griddata(
                self.points_valid,
                self.values_valid,
                query_points,
                method=method
            )
            return interpolated
        
        else:
            raise ValueError(f"Unknown interpolation method: {method}")
    
    def interpolate_grid(
        self,
        rlat_range: Tuple[float, float],
        rlon_range: Tuple[float, float],
        resolution: float,
        method: str = 'rbf'
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Interpolate over a regular grid.
        
        Args:
            rlat_range: (min, max) rotated latitude range
            rlon_range: (min, max) rotated longitude range
            resolution: Grid spacing in degrees
            method: Interpolation method ('rbf', 'linear', or 'cubic')
        
        Returns:
            Tuple of (rlat_grid, rlon_grid, values_grid)
        """
        # Create regular grid
        rlat_new = np.arange(rlat_range[0], rlat_range[1], resolution)
        rlon_new = np.arange(rlon_range[0], rlon_range[1], resolution)
        rlat_mesh, rlon_mesh = np.meshgrid(rlat_new, rlon_new, indexing='ij')
        
        # Flatten for interpolation
        rlat_query = rlat_mesh.flatten()
        rlon_query = rlon_mesh.flatten()
        
        # Interpolate
        values_interp = self.interpolate(rlat_query, rlon_query, method=method)
        
        # Reshape to grid
        values_grid = values_interp.reshape(rlat_mesh.shape)
        
        return rlat_mesh, rlon_mesh, values_grid
    
    def get_statistics(self) -> dict:
        """
        Get statistics about the interpolation grid.
        
        Returns:
            Dictionary with grid statistics
        """
        return {
            'variable': self.variable,
            'total_points': len(self.rlon_flat),
            'valid_points': len(self.values_valid),
            'nan_points': np.sum(~self.valid_mask),
            'value_min': np.min(self.values_valid) if len(self.values_valid) > 0 else np.nan,
            'value_max': np.max(self.values_valid) if len(self.values_valid) > 0 else np.nan,
            'value_mean': np.mean(self.values_valid) if len(self.values_valid) > 0 else np.nan,
            'rlat_range': (float(np.min(self.rlat_valid)), float(np.max(self.rlat_valid))),
            'rlon_range': (float(np.min(self.rlon_valid)), float(np.max(self.rlon_valid))),
            'kernel': self.kernel,
            'neighbors': self.neighbors
        }


def calculate_interpolation_error(
    interpolator: RemoInterpolator,
    test_points: np.ndarray,
    true_values: np.ndarray,
    method: str = 'rbf'
) -> dict:
    """
    Calculate interpolation error metrics.
    
    Args:
        interpolator: RemoInterpolator instance
        test_points: Array of shape (N, 2) with [rlat, rlon] test coordinates
        true_values: Array of shape (N,) with true values
        method: Interpolation method to test
    
    Returns:
        Dictionary with error metrics (MAE, RMSE, R²)
    """
    # Interpolate at test points
    predicted = interpolator.interpolate(
        test_points[:, 0],
        test_points[:, 1],
        method=method
    )
    
    # Calculate metrics
    errors = predicted - true_values
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors**2))
    
    # R² score
    ss_res = np.sum(errors**2)
    ss_tot = np.sum((true_values - np.mean(true_values))**2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'mean_error': np.mean(errors),
        'std_error': np.std(errors),
        'n_points': len(test_points)
    }
