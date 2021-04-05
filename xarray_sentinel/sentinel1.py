import os.path
import typing as T

import xarray as xr

from xarray_sentinel import esa_safe


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self, filename_or_obj: str, drop_variables: T.Optional[T.Tuple[str]] = None,
    ) -> xr.Dataset:
        manifest = esa_safe.open_manifest(filename_or_obj)
        product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
        product_attrs["groups"] = ["orbit"] + product_attrs["xs:instrument_mode_swaths"]
        ds = xr.Dataset(attrs=product_attrs)  # type: ignore
        return ds

    def guess_can_open(self, filename_or_obj: T.Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe"}
