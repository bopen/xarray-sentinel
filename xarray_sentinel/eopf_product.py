import logging
import pathlib
from typing import Any

import fsspec
import xarray as xr

from . import eopf_metadata, esa_safe, sentinel1


def open_datatree(
    product_urlpath: esa_safe.PathType,
    *,
    fs: fsspec.AbstractFileSystem | None = None,
    storage_options: dict[str, Any] | None = None,
    check_files_exist: bool = False,
    override_product_files: str | None = None,
    **kwargs: Any,
) -> xr.DataTree:
    product_name = pathlib.Path(product_urlpath).stem
    root = sentinel1.open_sentinel1_dataset(
        product_urlpath,
        fs=fs,
        storage_options=storage_options,
        check_files_exist=check_files_exist,
        override_product_files=override_product_files,
    )
    xarray_sentinel_groups = root.attrs["subgroups"]
    dt = xr.DataTree()
    for xarray_sentinel_group in xarray_sentinel_groups:
        _, _, pol_group = xarray_sentinel_group.partition("/")
        try:
            pol, _, dataset = pol_group.partition("/")
            eopf_product_name = f"{product_name}_{pol.upper()}"
            if not pol:
                continue
            if not dataset:
                if eopf_product_name not in dt.children:
                    product_ds = xr.Dataset(
                        attrs={
                            "other_metadata": eopf_metadata.build_other_metadata(
                                product_urlpath
                            ),
                            "stac_metadata": {},
                        }
                    )
                    dt[f"{eopf_product_name}"] = product_ds
                ds = sentinel1.open_sentinel1_dataset(
                    product_urlpath,
                    fs=fs,
                    storage_options=storage_options,
                    check_files_exist=check_files_exist,
                    override_product_files=override_product_files,
                    group=xarray_sentinel_group,
                )
                ds.attrs.clear()
                dt[f"{eopf_product_name}/measurement"] = ds.rename(
                    {"measurement": "slc"}
                )
            elif dataset in {"orbit", "attitude", "doppler_centroid", "gcp"}:
                ds = sentinel1.open_sentinel1_dataset(
                    product_urlpath,
                    fs=fs,
                    storage_options=storage_options,
                    check_files_exist=check_files_exist,
                    group=xarray_sentinel_group,
                    override_product_files=override_product_files,
                )
                ds.attrs.clear()
                dt[f"{eopf_product_name}/conditions/{dataset}"] = ds
            elif dataset in {"calibration", "noise_range", "noise_azimuth"}:
                ds = sentinel1.open_sentinel1_dataset(
                    product_urlpath,
                    fs=fs,
                    storage_options=storage_options,
                    check_files_exist=check_files_exist,
                    group=xarray_sentinel_group,
                    override_product_files=override_product_files,
                )
                ds.attrs.clear()
                dt[f"{eopf_product_name}/quality/{dataset}"] = ds
            else:
                print(f"Skipping {xarray_sentinel_group=}")
        except Exception:
            logging.exception(f"{xarray_sentinel_group=} failed to load")

    return dt
