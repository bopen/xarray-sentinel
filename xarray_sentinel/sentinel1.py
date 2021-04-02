import typing as T

import xarray as xr


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(   # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
    ) -> xr.Dataset:
        ds = xr.Dataset()
        return ds
