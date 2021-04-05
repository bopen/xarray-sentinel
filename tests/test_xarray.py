import pathlib

import xarray as xr

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_open_dataset() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert res.attrs["constellation"] == "sentinel-1"
    assert res.attrs["sar:product_type"] == "SLC"
    assert res.attrs["sar:instrument_mode"] == "IW"
