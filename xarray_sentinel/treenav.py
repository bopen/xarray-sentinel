import os

import xarray as xr


def get_subgroup(ds: xr.Dataset, subgroup: str) -> xr.Dataset:
    if "open_dataset_kwargs" not in ds.encoding:
        raise TypeError("Dataset must provide  encoding['open_dataset_kwargs']")

    open_dataset_kwargs = ds.encoding["open_dataset_kwargs"].copy()
    group = os.path.join(ds.attrs["group"], subgroup)
    open_dataset_kwargs["group"] = os.path.normpath(group)

    return xr.open_dataset(**open_dataset_kwargs)
