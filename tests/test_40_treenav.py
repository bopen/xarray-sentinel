import pathlib

import xarray as xr

from xarray_sentinel import treenav

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)


def test_get_subgroup() -> None:
    measurement_ds = xr.open_dataset(SLC_IW, group="IW1/VV")

    res = treenav.get_subgroup(measurement_ds, "orbit")

    assert isinstance(res, xr.Dataset)
    assert "position" in res.data_vars

    res = treenav.get_subgroup(res, "../attitude")

    assert isinstance(res, xr.Dataset)
    assert "roll" in res.data_vars
