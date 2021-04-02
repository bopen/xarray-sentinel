import typing as T

import xarray as xr


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
        **kwargs: T.Any,
    ) -> xr.Dataset:
        ds = xr.Dataset()
        return ds
