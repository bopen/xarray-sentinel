import pathlib

import pytest
import xarray as xr

dask = pytest.importorskip("dask")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_open_pol_dataset_iw_preferred_chunks() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/VV", chunks={})

    assert isinstance(res, xr.Dataset)
    assert len(res.dims) == 2
    assert res.measurement.chunks[0][0] == res.attrs["lines_per_burst"]


def test_open_pol_dataset_sm_preferred_chunks() -> None:
    product_path = (
        DATA_FOLDER
        / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="S3/VH", chunks={})

    assert isinstance(res, xr.Dataset)
    assert len(res.dims) == 2
    assert res.measurement.chunks[0][0] == 1024
