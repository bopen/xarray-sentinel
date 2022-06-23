import pathlib
from typing import Any

import pytest

from xarray_sentinel import reformat

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_to_group_zarr(tmpdir: Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    tmp_path = str(tmpdir.join("tmp.zarr"))

    reformat.to_group_zarr(product_path, tmp_path)


@pytest.mark.xfail
def test_to_group_netcdf(tmpdir: Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    tmp_path = str(tmpdir.join("tmp.nc"))

    reformat.to_group_netcdf(product_path, tmp_path)
