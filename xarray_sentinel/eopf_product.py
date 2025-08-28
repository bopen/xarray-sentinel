import pathlib
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
        swath, _, pol_group = xarray_sentinel_group.partition("/")
        pol, _, dataset = pol_group.partition("/")
        eopf_product_name = f"{product_name}_{swath}_{pol.upper()}"
        if not pol:
            continue
        if not dataset:
            measurement_ds = sentinel1.open_sentinel1_dataset(
                product_urlpath,
                fs=fs,
                storage_options=storage_options,
                check_files_exist=check_files_exist,
                override_product_files=override_product_files,
                group=xarray_sentinel_group,
                parse_eopf_metadata=True,
            ).rename(measurement="slc")
            if eopf_product_name not in dt.children:
                product_ds = xr.Dataset(
                    attrs={
                        "other_metadata": measurement_ds.attrs["other_metadata"],
                        "stac_discovery": measurement_ds.attrs["stac_discovery"],
                    }
                )
                dt[f"{eopf_product_name}"] = product_ds
            measurement_ds.attrs.clear()
            dt[f"{eopf_product_name}/measurement"] = measurement_ds
        elif dataset in {"orbit", "attitude", "dc_estimate", "gcp"}:
            ds = sentinel1.open_sentinel1_dataset(
                product_urlpath,
                fs=fs,
                storage_options=storage_options,
                check_files_exist=check_files_exist,
                group=xarray_sentinel_group,
                override_product_files=override_product_files,
            )
            if dataset == "dc_estimate":
                dataset = "doppler_centroid"
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

    return dt
