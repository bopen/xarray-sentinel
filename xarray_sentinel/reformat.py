import typing as T

import xarray as xr

from . import esa_safe


def to_group_zarr(product_path: esa_safe.PathType, output_store: T.Any) -> None:
    root = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore
    root.to_zarr(output_store, mode="w")

    for group in root.attrs["subgroups"]:
        group_ds = xr.open_dataset(product_path, engine="sentinel-1", group=group)  # type: ignore
        group_ds.to_zarr(output_store, mode="a", group=group)
