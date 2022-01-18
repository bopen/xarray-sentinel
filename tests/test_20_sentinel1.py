import pathlib

import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)
SLC_IW1_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_calibration = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "calibration"
    / "calibration-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_measurement = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "measurement"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.tiff"
)
SLC_S3_VV_annotation = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
    / "annotation"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.xml"
)
SLC_S3_VV_measurement = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
    / "measurement"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.tiff"
)
GRD_IW_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_open_calibration_dataset() -> None:
    res = sentinel1.open_calibration_dataset(SLC_IW1_VV_calibration)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line", "pixel"}


def test_open_coordinateConversion_dataset() -> None:
    res = sentinel1.open_coordinateConversion_dataset(GRD_IW_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"azimuth_time", "degree"}


def test_open_gcp_dataset() -> None:
    res = sentinel1.open_gcp_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line", "pixel", "azimuth_time", "slant_range_time"}


def test_open_attitude_dataset() -> None:
    res = sentinel1.open_attitude_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"azimuth_time"}


def test_open_orbit_dataset() -> None:
    res = sentinel1.open_orbit_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"axis", "azimuth_time"}


def test_open_dc_estimate_dataset() -> None:
    res = sentinel1.open_dc_estimate_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"degree", "azimuth_time"}


def test_open_azimuth_fm_rate_dataset() -> None:
    res = sentinel1.open_azimuth_fm_rate_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"degree", "azimuth_time"}


def test_open_pol_dataset_iw() -> None:
    res = sentinel1.open_pol_dataset(SLC_IW1_VV_measurement, SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"line", "pixel"}
    assert set(res.coords) == {"slant_range_time", "azimuth_time", "line", "pixel"}


@pytest.mark.xfail
def test_open_pol_dataset_sm() -> None:
    res = sentinel1.open_pol_dataset(SLC_S3_VV_measurement, SLC_S3_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"slant_range_time", "azimuth_time"}
    assert set(res.coords) == {"slant_range_time", "azimuth_time", "line", "pixel"}


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


def test_normalise_group() -> None:
    assert sentinel1.normalise_group(None) == ("", None)
    assert sentinel1.normalise_group("/") == ("", None)
    assert sentinel1.normalise_group("IW1") == ("IW1", None)
    assert sentinel1.normalise_group("/IW1") == ("IW1", None)
    assert sentinel1.normalise_group("/IW1/VH/0") == ("IW1/VH", 0)
    assert sentinel1.normalise_group("/IW1/VH/orbit") == ("IW1/VH/orbit", None)


def test_open_dataset() -> None:
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/gcp",
        "IW1/VV/attitude",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    res = sentinel1.open_sentinel1_dataset(SLC_IW)

    assert isinstance(res, xr.Dataset)
    assert len(res.data_vars) == 0
    assert set(res.attrs["subgroups"]) >= expected_groups

    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1")

    assert isinstance(res, xr.Dataset)
    assert len(res.data_vars) == 0

    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/orbit")

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"axis": 3, "azimuth_time": 17}

    with pytest.raises(ValueError):
        sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/non-existent")


def test_open_dataset_virtual_groups() -> None:
    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/0")

    assert isinstance(res, xr.Dataset)
    assert len(res.data_vars) == 1
    assert res.attrs["burst_index"] == 0


def test_open_dataset_chunks() -> None:
    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV", chunks=1000)

    assert isinstance(res, xr.Dataset)
    assert len(res.dims) == 2
    assert np.allclose(res.measurement.chunks[0][:-1], 1000)
    assert np.allclose(res.measurement.chunks[1][:-1], 1000)
    assert not np.all(np.isnan(res.measurement))


def test_crop_burst_dataset() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")

    res1 = sentinel1.crop_burst_dataset(swath_ds, 8)

    assert set(res1.dims) == {"azimuth_time", "slant_range_time"}
    assert res1.dims["azimuth_time"] == swath_ds.attrs["lines_per_burst"]

    res2 = sentinel1.crop_burst_dataset(swath_ds, azimuth_anx_time=2210)

    assert res2.equals(res1)

    res3 = sentinel1.crop_burst_dataset(
        swath_ds, azimuth_anx_time=2213, use_center=True
    )

    assert res3.equals(res1)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds, burst_index=8, azimuth_anx_time=2213)

    with pytest.raises(IndexError):
        sentinel1.crop_burst_dataset(swath_ds, burst_index=-1)
