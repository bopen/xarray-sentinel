import pathlib

import pytest
import xarray as xr

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_open_dataset_root() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert res.attrs["constellation"] == "sentinel-1"
    assert res.attrs["sar:product_type"] == "SLC"
    assert res.attrs["sar:instrument_mode"] == "IW"

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)

    product_path = product_path / "manifest.safe"

    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)


def test_open_dataset_orbit() -> None:
    manifest_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(manifest_path, engine="sentinel-1", group="IW1/orbit")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"time"}


def test_open_dataset_attitude() -> None:
    manifest_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(manifest_path, engine="sentinel-1", group="IW1/attitude")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"time"}


def test_open_dataset_gcp() -> None:
    annotation_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(annotation_path, engine="sentinel-1", group="IW1/gcp")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"azimuth_time", "slant_range_time"}


def test_open_subswath() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert not res.variables


@pytest.mark.xfail
def test_open_burst() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/R168-N118-E0472")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"x": 21632, "y": 1501}
    assert set(res.variables) == {"VH", "VV", "x", "y"}
