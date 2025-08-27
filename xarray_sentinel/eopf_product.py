import logging
from typing import Any

import fsspec
import xarray as xr

from . import esa_safe, sentinel1


def open_datatree(
    product_urlpath: esa_safe.PathType,
    *,
    fs: fsspec.AbstractFileSystem | None = None,
    storage_options: dict[str, Any] | None = None,
    check_files_exist: bool = False,
    override_product_files: str | None = None,
    parse_geospatial_attrs: bool = True,
    **kwargs: Any,
) -> xr.DataTree:
    root = sentinel1.open_sentinel1_dataset(
        product_urlpath,
        fs=fs,
        storage_options=storage_options,
        check_files_exist=check_files_exist,
    )
    dt = xr.DataTree()
    for group in root.attrs["subgroups"]:
        subgroup = group.partition("/")[2]
        try:
            product_type, _, dataset = subgroup.partition("/")
            if not product_type:
                continue
            if not dataset:
                dt[f"{product_type}/measurement"] = sentinel1.open_sentinel1_dataset(
                    product_urlpath,
                    fs=fs,
                    storage_options=storage_options,
                    check_files_exist=check_files_exist,
                    group=group,
                )
            else:
                dt[f"{product_type}/conditions/{dataset}"] = (
                    sentinel1.open_sentinel1_dataset(
                        product_urlpath,
                        fs=fs,
                        storage_options=storage_options,
                        check_files_exist=check_files_exist,
                        group=group,
                    )
                )
        except Exception:
            logging.exception(f"{group=} failed to load")

    return dt
