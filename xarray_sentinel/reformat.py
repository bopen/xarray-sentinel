import typing as T

import xarray as xr

from . import esa_safe


def to_group_zarr(product_path: esa_safe.PathType, output_store: T.Any) -> None:
    root = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore
    root.to_zarr(output_store, mode="w")

    for group in root.attrs["subgroups"]:
        group_ds = xr.open_dataset(product_path, engine="sentinel-1", group=group)  # type: ignore
        group_ds.to_zarr(output_store, mode="a", group=group)


# Apparently there is no way to save SLC images because "netcdf4" doesn't support complex data
# and "n5necdf" crashes on same name dimensions.
def to_group_netcdf(
    product_path: esa_safe.PathType, output_store: str, engine: T.Optional[str] = None
) -> None:
    root = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore
    root.to_netcdf(output_store, mode="w", engine=engine)

    for group in root.attrs["subgroups"]:
        group_ds = xr.open_dataset(product_path, engine="sentinel-1", group=group)  # type: ignore
        group_ds.to_netcdf(output_store, mode="a", group=group, engine=engine)
