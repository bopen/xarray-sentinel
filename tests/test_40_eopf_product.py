import pathlib

import xarray as xr

from xarray_sentinel import eopf_product

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
)


def test_open_datatree() -> None:
    res = eopf_product.open_datatree(SLC_IW)

    assert isinstance(res, xr.DataTree)
