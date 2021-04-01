import xarray as xr


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(
        self, filename_or_obj, *, drop_variables=None,
    ):
        ds = xr.Dataset()
        return ds
