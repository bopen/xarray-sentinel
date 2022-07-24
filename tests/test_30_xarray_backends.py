import pathlib

import pytest
import xarray as xr

from xarray_sentinel import esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


COMMON_ATTRIBUTES = {
    "family_name": "SENTINEL-1",
    "number": "B",
    "mode": "IW",
    "swaths": ["IW1", "IW2", "IW3"],
    "orbit_number": 26269,
    "relative_orbit_number": 168,
    "pass": "DESCENDING",
    "ascending_node_time": "2021-04-01T04:49:55.637823",
    "transmitter_receiver_polarisations": ["VV", "VH"],
    "product_type": "SLC",
}


SENTINEL1_SLC_PRODUCTS = [
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
        / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE",
        "S3/VH",
    ),
]

SENTINEL1_GRD_PRODUCTS = [
    (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE",
        "IW/VV",
    ),
]
SENTINEL1_PRODUCTS = SENTINEL1_SLC_PRODUCTS + SENTINEL1_GRD_PRODUCTS


def test_open_dataset_root() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")

    assert isinstance(res, xr.Dataset)
    for attr_name in COMMON_ATTRIBUTES:
        assert attr_name in res.attrs
        assert res.attrs[attr_name] == COMMON_ATTRIBUTES[attr_name]

    res = xr.open_dataset(product_path)

    assert isinstance(res, xr.Dataset)

    product_path = product_path / "manifest.safe"

    res = xr.open_dataset(product_path, engine="sentinel-1")

    assert isinstance(res, xr.Dataset)

    res = xr.open_dataset(product_path)

    assert isinstance(res, xr.Dataset)

    with pytest.raises(ValueError):
        xr.open_dataset("")


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_SLC_PRODUCTS)
def test_open_dataset_polarisation_slc(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=swath_pol)

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"} or set(res.dims) == {
        "azimuth_time",
        "slant_range_time",
    }
    assert set(res.coords) == {"azimuth_time", "slant_range_time", "line", "pixel"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_GRD_PRODUCTS)
def test_open_dataset_polarisation_grd(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=swath_pol)

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"} or set(res.dims) == {
        "azimuth_time",
        "ground_range",
    }
    assert set(res.coords) == {"azimuth_time", "ground_range", "line", "pixel"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_orbit(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/orbit")

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"axis", "azimuth_time"}
    assert set(res.variables) == {"azimuth_time", "axis", "velocity", "position"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_attitude(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(
        product_path, engine="sentinel-1", group=f"{swath_pol}/attitude"
    )

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
    res = xr.open_dataset(product_path, engine="sentinel-1", group=f"{swath_pol}/gcp")

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"azimuth_time", "slant_range_time"}


@pytest.mark.parametrize("product_path,swath_pol", SENTINEL1_PRODUCTS)
def test_open_dataset_dc_estimate(
    product_path: esa_safe.PathType,
    swath_pol: str,
) -> None:
    res = xr.open_dataset(
        product_path, engine="sentinel-1", group=f"{swath_pol}/dc_estimate"
    )

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
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/VV")

    assert isinstance(res, xr.Dataset)
    for attr_name in COMMON_ATTRIBUTES:
        assert attr_name in res.attrs
        assert res.attrs[attr_name] == COMMON_ATTRIBUTES[attr_name]

    assert set(res.dims) == {"line", "pixel"}
    assert set(res.variables) == expected_variables


def test_burst_id_attribute() -> None:
    product_path = (
        DATA_FOLDER
        / "S1A_IW_SLC__1SDH_20220414T102209_20220414T102236_042768_051AA4_E677.SAFE"
    )

    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/HH")
    assert "burst_ids" in res.attrs
    assert len(res.attrs["burst_ids"]) == res.attrs["number_of_bursts"]

    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1", group="IW1/VV")
    assert "burst_ids" not in res.attrs


def test_open_calibration_dataset() -> None:
    annotation_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(
        annotation_path, engine="sentinel-1", group="IW1/VV/calibration"
    )

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"}
