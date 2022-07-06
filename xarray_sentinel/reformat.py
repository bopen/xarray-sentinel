from __future__ import annotations

from typing import Any, Dict, Optional

import rasterio
import xarray as xr

from . import esa_safe


def to_group_zarr(
    product_path: esa_safe.PathType,
    output_store: Any,
    groups: Optional[Dict[str, str]] = None,
) -> None:
    root = xr.open_dataset(product_path, engine="sentinel-1")
    root.to_zarr(output_store, mode="w")

    if groups is None:
        groups = {g: g for g in root.attrs["subgroups"]}

    for group_out, group_in in groups.items():
        try:
            group_ds = xr.open_dataset(
                product_path, engine="sentinel-1", group=group_in
            )
            group_ds.to_zarr(output_store, mode="a", group=group_out)
        except (FileNotFoundError, rasterio.RasterioIOError):
            pass


# Apparently there is no way to save SLC images because "netcdf4" doesn't support complex data
# and "n5necdf" crashes on same name dimensions.
def to_group_netcdf(
    product_path: esa_safe.PathType,
    output_store: str,
    groups: Optional[Dict[str, str]] = None,
    engine: xr.backends.api.T_NetcdfEngine | None = None,
) -> None:
    root = xr.open_dataset(product_path, engine="sentinel-1")
    root.to_netcdf(output_store, mode="w", engine=engine)

    if groups is None:
        groups = {g: g for g in root.attrs["subgroups"]}

    for group_out, group_in in groups.items():
        try:
            group_ds = xr.open_dataset(
                product_path, engine="sentinel-1", group=group_in
            )
            group_ds.to_netcdf(output_store, mode="a", group=group_out, engine=engine)
        except (FileNotFoundError, rasterio.RasterioIOError):
            pass
