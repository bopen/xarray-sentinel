import xarray as xr


def test_open_dataset() -> None:
    ds = xr.open_dataset("dummy", engine="sentinel-1")  # type: ignore
    assert isinstance(ds, xr.Dataset)
