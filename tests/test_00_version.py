import xarray_sentinel


def test_version() -> None:
    assert xarray_sentinel.__version__ != "999"
