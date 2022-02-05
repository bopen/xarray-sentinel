import pathlib

import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import esa_safe, sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)
SLC_IW1_VV_annotation = (
    SLC_IW
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_calibration = (
    SLC_IW
    / "annotation"
    / "calibration"
    / "calibration-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_noise = (
    SLC_IW
    / "annotation"
    / "calibration"
    / "noise-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_measurement = (
    SLC_IW
    / "measurement"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.tiff"
)
SLC_S3 = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
)
SLC_S3_VV_annotation = (
    SLC_S3
    / "annotation"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.xml"
)
SLC_S3_VV_measurement = (
    SLC_S3
    / "measurement"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.tiff"
)
GRD_IW_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_get_fs_path() -> None:
    fs, path = sentinel1.get_fs_path(str(SLC_IW))

    assert path == str(SLC_IW.absolute())

    fs, path = sentinel1.get_fs_path(SLC_IW, fs)

    assert path == str(SLC_IW)

    with pytest.raises(ValueError):
        sentinel1.get_fs_path("non-existent-path/*")

    with pytest.raises(ValueError):
        sentinel1.get_fs_path(DATA_FOLDER / "*")


def test_normalise_group() -> None:
    assert sentinel1.normalise_group(None) == ("", None)
    assert sentinel1.normalise_group("/") == ("", None)
    assert sentinel1.normalise_group("IW1") == ("IW1", None)
    assert sentinel1.normalise_group("/IW1") == ("IW1", None)
    assert sentinel1.normalise_group("/IW1/VH/0") == ("IW1/VH", 0)
    assert sentinel1.normalise_group("/IW1/VH/orbit") == ("IW1/VH/orbit", None)


def test_open_calibration_dataset() -> None:
    res = sentinel1.open_calibration_dataset(SLC_IW1_VV_calibration)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line", "pixel"}


def test_open_noise_range_dataset() -> None:
    res = sentinel1.open_noise_range_dataset(SLC_IW1_VV_noise)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line", "pixel"}


def test_open_noise_azimuth_dataset() -> None:
    res = sentinel1.open_noise_azimuth_dataset(SLC_IW1_VV_noise)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line"}


def test_open_coordinate_conversion_dataset() -> None:
    res = sentinel1.open_coordinate_conversion_dataset(GRD_IW_VV_annotation)

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
    _, product_files = esa_safe.parse_manifest_sentinel1(SLC_S3 / "manifest.safe")
    expected_groups = {
        "S3",
        "S3/VV",
        "S3/VV/attitude",
        "S3/VV/gcp",
        "S3/VV/orbit",
        "S3/VV/dc_estimate",
        "S3/VV/azimuth_fm_rate",
        "S3/VV/coordinate_conversion",
        "S3/VV/calibration",
        "S3/VV/noise_range",
        "S3/VV/noise_azimuth",
        "S3",
        "S3/VH",
        "S3/VH/attitude",
        "S3/VH/gcp",
        "S3/VH/orbit",
        "S3/VH/dc_estimate",
        "S3/VH/azimuth_fm_rate",
        "S3/VH/coordinate_conversion",
        "S3/VH/calibration",
        "S3/VH/noise_range",
        "S3/VH/noise_azimuth",
    }

    res = sentinel1.find_available_groups(product_files, str(SLC_IW))

    assert set(res) == expected_groups

    res = sentinel1.find_available_groups(
        product_files, str(SLC_IW), check_files_exist=True
    )
    assert res == {}


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
        "IW1/VV/noise_range",
        "IW1/VV/noise_azimuth",
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
    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV")

    assert isinstance(res, xr.Dataset)
    assert len(res.dims) == 2
    assert res.measurement.chunks[0][0] == res.attrs["lines_per_burst"]
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


def test_calibrate_amplitude() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")
    burst_ds = sentinel1.crop_burst_dataset(swath_ds, burst_index=8)
    calibration_ds = sentinel1.open_calibration_dataset(SLC_IW1_VV_calibration)

    res = sentinel1.calibrate_amplitude(
        burst_ds.measurement, calibration_ds["betaNought"]
    )

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.complex64)


def test_calibrate_intensity() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")
    burst_ds = sentinel1.crop_burst_dataset(swath_ds, burst_index=8)
    calibration_ds = sentinel1.open_calibration_dataset(SLC_IW1_VV_calibration)

    res = sentinel1.calibrate_intensity(
        burst_ds.measurement, calibration_ds["betaNought"]
    )

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.float32)
