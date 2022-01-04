import pathlib

import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_build_burst_id() -> None:
    lat = 11.8475875
    lon = 47.16626783
    relative_orbit = 168

    burst_id = sentinel1.build_burst_id(lat=lat, lon=lon, relative_orbit=relative_orbit)

    assert burst_id == "R168-N118-E0472"


def test_find_avalable_groups() -> None:
    base_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    ancillary_data_paths = {
        "IW1": {
            "VV": {
                "s1Level1ProductSchema": f"{base_path}/annotation/"
                + "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml",
                "s1Level1CalibrationSchema": f"{base_path}/annotation/calibration/"
                + "calibration-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml",
            },
        },
    }
    product_attrs = {"sat:relative_orbit": 168}
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/attitude",
        "IW1/VV/gcp",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    groups = sentinel1.find_avalable_groups(ancillary_data_paths, product_attrs)
    assert set(groups) == expected_groups


def test_compute_burst_centres() -> None:
    gcp = xr.Dataset(
        {
            "latitude": xr.DataArray(
                np.arange(5).reshape(5, 1), dims=("azimuth_time", "slant_range_time")
            ),
            "longitude": xr.DataArray(
                np.arange(5).reshape(5, 1) * 10,
                dims=("azimuth_time", "slant_range_time"),
            ),
        },
        attrs={"burst_count": 4},
    )
    lat, lon = sentinel1.compute_burst_centres(gcp)
    assert np.allclose(lat, [0.5, 1.5, 2.5, 3.5])
    assert np.allclose(lon, [5, 15, 25, 35])


def test_open_dataset() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/gcp",
        "IW1/VV/attitude",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    res = sentinel1.open_dataset(product_path)

    assert isinstance(res, xr.Dataset)
    assert set(res.attrs["subgroups"]) >= expected_groups

    res = sentinel1.open_dataset(product_path, group="IW1/VV/orbit")

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"axis": 3, "azimuth_time": 17}

    with pytest.raises(ValueError):
        sentinel1.open_dataset(product_path, group="IW1/VV/non-existent")


def test_open_dataset_zip() -> None:
    zip_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.zip"
    )
    zip_urlpath = f"zip://*/manifest.safe::{zip_path}"
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/gcp",
        "IW1/VV/attitude",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    res = sentinel1.open_dataset(zip_urlpath)

    assert isinstance(res, xr.Dataset)
    assert set(res.attrs["subgroups"]) >= expected_groups

    res = sentinel1.open_dataset(zip_urlpath, group="IW1/VV/orbit")

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"axis": 3, "azimuth_time": 17}


@pytest.mark.skip
def test_open_dataset_chunks_bursts() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = sentinel1.open_dataset(product_path, group="IW1/R168-N471-E0118", chunks=1000)

    assert isinstance(res, xr.Dataset)
    assert len(res.VH.dims) == 2
    assert np.allclose(res.VH.chunks[0][:-1], 1000)
    assert np.allclose(res.VH.chunks[1][:-1], 1000)
    assert not np.all(np.isnan(res.VH))
    assert not np.all(np.isnan(res.VH))
