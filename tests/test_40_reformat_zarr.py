import pathlib
from typing import Any

import pytest

from xarray_sentinel import reformat

pytest.importorskip("zarr")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_to_group_zarr(tmpdir: Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    )
    tmp_path = str(tmpdir.join("tmp.zarr"))
    groups = {"IW/VV/gcp": "IW/VV/gcp", "IW/VH/attitude": "IW/VH/attitude"}

    reformat.to_group_zarr(product_path, tmp_path, groups)

    reformat.to_group_zarr(product_path, tmp_path)
