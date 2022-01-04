import pathlib
import typing as T

import pytest

from xarray_sentinel import reformat

pytest.importorskip("netCDF4")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_to_group_netcdf(tmpdir: T.Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    tmp_path = str(tmpdir.join("tmp.nc"))
    groups = {"IW1/VV/gcp": "IW1/VV/gcp", "IW2/VH/attitude": "IW2/VH/attitude"}

    reformat.to_group_netcdf(product_path, tmp_path, groups, engine="netcdf4")
