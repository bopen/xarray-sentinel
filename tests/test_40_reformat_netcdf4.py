import pathlib
from typing import Any

import pytest

from xarray_sentinel import reformat

pytest.importorskip("netCDF4")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_to_group_netcdf(tmpdir: Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    )
    tmp_path = str(tmpdir.join("tmp.nc"))
    groups = {"IW/VV/gcp": "IW/VV/gcp", "IW/VH/attitude": "IW/VH/attitude"}

    reformat.to_group_netcdf(product_path, tmp_path, groups, engine="netcdf4")

    reformat.to_group_netcdf(product_path, tmp_path, engine="netcdf4")
