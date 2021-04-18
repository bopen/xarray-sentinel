import pathlib
import typing as T

import pytest
import xarray as xr

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def assert_common_attributes(attrs: T.Dict[T.Hashable, T.Any]) -> None:
    assert attrs["constellation"] == "sentinel-1"
    assert attrs["platform"] == "sentinel-1b"
    assert attrs["instrument"] == ["c-sar"]
    assert attrs["sat:orbit_state"] == "descending"
    assert attrs["sat:absolute_orbit"] == 26269
    assert attrs["sat:relative_orbit"] == 168
    assert attrs["sat:anx_datetime"] == "2021-04-01T04:49:55.637823Z"
    assert attrs["sar:frequency_band"] == "C"
    assert attrs["sar:instrument_mode"] == "IW"
    assert attrs["sar:polarizations"] == ["VV", "VH"]
    assert attrs["sar:product_type"] == "SLC"
    assert attrs["xs:instrument_mode_swaths"] == ["IW1", "IW2", "IW3"]


def test_open_dataset_root() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert_common_attributes(res.attrs)

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
    assert_common_attributes(res.attrs)
    assert not res.variables


@pytest.mark.xfail
def test_open_burst() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/R168-N118-E0472")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert_common_attributes(res.attrs)
    assert res.dims == {"x": 21632, "y": 1501}
    assert set(res.variables) == {"VH", "VV", "x", "y"}
