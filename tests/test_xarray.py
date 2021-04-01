import xarray as xr


def test_open_dataset():
    ds = xr.open_dataset("dummy", engine="sentinel-1")
    assert isinstance(ds, xr.Dataset)
