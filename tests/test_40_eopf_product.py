import pathlib

import xarray as xr

from xarray_sentinel import eopf_product

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)


def test_open_datatree() -> None:
    res = eopf_product.open_datatree(SLC_IW)

    assert isinstance(res, xr.DataTree)
