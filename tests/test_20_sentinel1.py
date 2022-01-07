import pathlib

import fsspec  # type: ignore
import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)


def test_get_fs_path() -> None:
    fs, path = sentinel1.get_fs_path(SLC_IW)

    assert isinstance(fs, fsspec.AbstractFileSystem)
    assert path == str(SLC_IW)

    fs2, path2 = sentinel1.get_fs_path(path, fs=fs)

    assert fs2 is fs
    assert path2 is path

    with pytest.raises(ValueError):
        sentinel1.get_fs_path("dummy*")

    with pytest.raises(ValueError):
        sentinel1.get_fs_path("*")


def test_build_burst_id() -> None:
    lat = 11.8475875
    lon = 47.16626783
    relative_orbit = 168

    burst_id = sentinel1.build_burst_id(lat=lat, lon=lon, relative_orbit=relative_orbit)

    assert burst_id == "R168-N118-E0472"


def test_find_avalable_groups() -> None:
    ancillary_data_paths = {
        "IW1": {
            "VV": {
                "s1Level1ProductSchema": f"{SLC_IW}/annotation/"
                + "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml",
                "s1Level1CalibrationSchema": f"{SLC_IW}/annotation/calibration/"
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
        "IW1/VV/dc_estimate",
        "IW1/VV/azimuth_fm_rate",
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
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/gcp",
        "IW1/VV/attitude",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    res = sentinel1.open_dataset(SLC_IW)

    assert isinstance(res, xr.Dataset)
    assert set(res.attrs["subgroups"]) >= expected_groups

    res = sentinel1.open_dataset(SLC_IW, group="IW1/VV/orbit")

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"axis": 3, "azimuth_time": 17}

    with pytest.raises(ValueError):
        sentinel1.open_dataset(SLC_IW, group="IW1/VV/non-existent")


def test_open_dataset_chunks() -> None:
    res = sentinel1.open_dataset(SLC_IW, group="IW1/VV", chunks=1000)

    assert isinstance(res, xr.Dataset)
    assert len(res.dims) == 2
    assert np.allclose(res.measurement.chunks[0][:-1], 1000)
    assert np.allclose(res.measurement.chunks[1][:-1], 1000)
    assert not np.all(np.isnan(res.measurement))


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


def test_crop_burst_dataset() -> None:
    swath_polarisation_ds = sentinel1.open_dataset(SLC_IW, group="IW1/VH")

    res = sentinel1.crop_burst_dataset(swath_polarisation_ds, 8)

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert res.dims["azimuth_time"] == swath_polarisation_ds.attrs["lines_per_burst"]
