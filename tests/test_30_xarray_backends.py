import pathlib

import pytest
import xarray as xr

from xarray_sentinel import esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


COMMON_ATTRIBUTES = {
    "constellation": "sentinel-1",
    "platform": "sentinel-1b",
    "instrument": ["c-sar"],
    "sat:orbit_state": "descending",
    "sat:absolute_orbit": 26269,
    "sat:relative_orbit": 168,
    "sat:anx_datetime": "2021-04-01T04:49:55.637823Z",
    "sar:frequency_band": "C",
    "sar:instrument_mode": "IW",
    "sar:polarizations": ["VV", "VH"],
    "sar:product_type": "SLC",
    "xs:instrument_mode_swaths": ["IW1", "IW2", "IW3"],
}


SENTINEL1_PRODUCTS = [
    (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE",
        "IW1/VV",
    ),
    (
        DATA_FOLDER
        / "S1A_EW_SLC__1SDH_20210403T122536_20210403T122630_037286_046484_8152.SAFE",
        "EW1/HH",
    ),
    (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE",
        "IW/VV",
    ),
    (
        DATA_FOLDER
        / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE",
        "S3/VV",
    ),
]


def test_open_dataset_root() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    for attr_name in COMMON_ATTRIBUTES:
        assert attr_name in res.attrs
        assert res.attrs[attr_name] == COMMON_ATTRIBUTES[attr_name]

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)

    product_path = product_path / "manifest.safe"

    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)

    with pytest.raises(ValueError):
        xr.open_dataset(None)  # type: ignore


@pytest.mark.xfail
@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_polarisation(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=swath_pol)  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"} or set(res.dims) == {
        "azimuth_time",
        "slant_range_time",
    }
    assert set(res.coords) == {"azimuth_time", "slant_range_time", "line", "pixel"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_orbit(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/orbit")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"axis", "azimuth_time"}
    assert set(res.variables) == {"azimuth_time", "axis", "velocity", "position"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_attitude(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/attitude")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"azimuth_time"}
    expected = {
        "azimuth_time",
        "roll",
        "pitch",
        "yaw",
        "q0",
        "q1",
        "q2",
        "q3",
        "wx",
        "wy",
        "wz",
    }
    assert set(res.variables) == expected


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_gcp(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/gcp")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"azimuth_time", "slant_range_time"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_dc_estimate(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/dc_estimate")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"azimuth_time", "degree"}


def test_open_pol_dataset() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    expected_variables = {
        "measurement",
        "line",
        "pixel",
        "slant_range_time",
        "azimuth_time",
    }
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/VV")  # type: ignore

    assert isinstance(res, xr.Dataset)
    for attr_name in COMMON_ATTRIBUTES:
        assert attr_name in res.attrs
        assert res.attrs[attr_name] == COMMON_ATTRIBUTES[attr_name]

    assert set(res.dims) == {"line", "pixel"}
    assert set(res.variables) == expected_variables


def test_open_calibration_dataset() -> None:
    annotation_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(annotation_path, engine="sentinel-1", group="IW1/VV/calibration")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"}
