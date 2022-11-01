import pathlib

import numpy as np
import pytest
import shapely.geometry
import shapely.wkt
import xarray as xr

from xarray_sentinel import esa_safe, sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW_V340 = (
    DATA_FOLDER
    / "S1A_IW_SLC__1SDH_20220414T102209_20220414T102236_042768_051AA4_E677.SAFE"
)

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
SLC_S3_VH_annotation = (
    SLC_S3
    / "annotation"
    / "s1a-s3-slc-vh-20210401t152855-20210401t152914-037258-04638e-001.xml"
)
SLC_S3_VH_measurement = (
    SLC_S3
    / "measurement"
    / "s1a-s3-slc-vh-20210401t152855-20210401t152914-037258-04638e-001.tiff"
)
GRD_IW = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
)
GRD_IW_VV_annotation = (
    GRD_IW
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_get_fs_path() -> None:
    fs, path = sentinel1.get_fs_path(str(SLC_IW))

    assert path == str((SLC_IW / "manifest.safe").absolute())

    fs, path = sentinel1.get_fs_path(SLC_IW, fs)

    assert path == str((SLC_IW / "manifest.safe"))

    with pytest.raises(TypeError):
        sentinel1.get_fs_path("*", fs=fs, storage_options={})

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

    with pytest.raises(TypeError):
        sentinel1.open_coordinate_conversion_dataset(SLC_IW1_VV_annotation)


def test_open_gcp_dataset() -> None:
    expected_geospatial_bounds = (
        "POLYGON((11.26870151724317 47.24053130234206,"
        "10.876144717121 45.73265733767158,12.04397933341514 45.57910451206848,"
        "12.42647347821595 47.09200435560957,11.26870151724317 47.24053130234206))"
    )
    expected_polygon = shapely.wkt.loads(expected_geospatial_bounds)
    expected_geospatial_bbox = (
        10.876144717121,
        45.57910451206848,
        12.42647347821595,
        47.24053130234206,
    )

    res = sentinel1.open_gcp_dataset(SLC_IW1_VV_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.coords) == {"line", "pixel", "azimuth_time", "slant_range_time"}
    assert isinstance(res.attrs["geospatial_bounds"], str)
    assert shapely.wkt.loads(res.attrs["geospatial_bounds"]).is_valid
    assert shapely.wkt.loads(res.attrs["geospatial_bounds"]).equals(expected_polygon)
    assert res.attrs["geospatial_bounds"] == expected_geospatial_bounds
    geospatial_bbox = (
        res.attrs["geospatial_lon_min"],
        res.attrs["geospatial_lat_min"],
        res.attrs["geospatial_lon_max"],
        res.attrs["geospatial_lat_max"],
    )
    assert np.allclose(geospatial_bbox, expected_geospatial_bbox)


def test_get_footprint_linestring() -> None:
    gcp_ds = sentinel1.open_gcp_dataset(SLC_IW1_VV_annotation)
    expected_linestring = [
        (11.26870151724317, 47.24053130234206),
        (10.876144717121, 45.73265733767158),
        (12.04397933341514, 45.57910451206848),
        (12.42647347821595, 47.09200435560957),
        (11.26870151724317, 47.24053130234206),
    ]

    res = sentinel1.get_footprint_linestring(
        gcp_ds.azimuth_time, gcp_ds.slant_range_time, gcp_ds
    )

    polygon = shapely.geometry.Polygon(res)
    assert polygon.is_valid
    assert shapely.geometry.polygon.orient(polygon, 1) == polygon
    assert res == expected_linestring

    res = sentinel1.get_footprint_linestring(
        gcp_ds.azimuth_time[::-1], gcp_ds.slant_range_time, gcp_ds
    )

    polygon = shapely.geometry.Polygon(res)
    assert polygon.is_valid
    assert shapely.geometry.polygon.orient(polygon, 1) == polygon


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

    first_line = np.datetime64(res.attrs["product_first_line_utc_time"])
    last_line = np.datetime64(res.attrs["product_last_line_utc_time"])
    assert res.azimuth_time[0] == first_line
    assert res.azimuth_time[-1] == last_line

    expected_geospatial_bounds = (
        "POLYGON((11.26870151724317 47.24053130234206,"
        "10.876144717121 45.73265733767158,12.04397933341514 45.57910451206848,"
        "12.42647347821595 47.09200435560957,11.26870151724317 47.24053130234206))"
    )
    gcp_ds = sentinel1.open_gcp_dataset(SLC_IW1_VV_annotation)

    res = sentinel1.open_pol_dataset(
        SLC_IW1_VV_measurement, SLC_IW1_VV_annotation, gcp=gcp_ds
    )

    assert res.attrs["geospatial_bounds"] == expected_geospatial_bounds


def test_open_pol_dataset_sm() -> None:
    res = sentinel1.open_pol_dataset(SLC_S3_VH_measurement, SLC_S3_VH_annotation)

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"slant_range_time", "azimuth_time"}
    assert set(res.coords) == {"slant_range_time", "azimuth_time", "line", "pixel"}

    first_line = np.datetime64(res.attrs["product_first_line_utc_time"])
    last_line = np.datetime64(res.attrs["product_last_line_utc_time"])
    assert res.azimuth_time[0] == first_line
    assert res.azimuth_time[-1] == last_line


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


def test_open_sentinel1_dataset() -> None:
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
    assert res.dims == {"axis": 3, "azimuth_time": 17}  # type: ignore

    with pytest.raises(ValueError):
        sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/non-existent")


def test_open_dataset_virtual_groups() -> None:
    res = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/0")

    assert isinstance(res, xr.Dataset)
    assert len(res.data_vars) == 1
    assert res.attrs["burst_index"] == 0


def test_crop_burst_dataset() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW_V340, group="IW1/HH")

    res1 = sentinel1.crop_burst_dataset(swath_ds, 8)

    assert set(res1.dims) == {"azimuth_time", "slant_range_time"}
    assert res1.dims["azimuth_time"] == swath_ds.attrs["lines_per_burst"]

    res2 = sentinel1.crop_burst_dataset(swath_ds, azimuth_anx_time=2210)

    assert res2.equals(res1)

    res3 = sentinel1.crop_burst_dataset(
        swath_ds, azimuth_anx_time=2213, use_center=True
    )

    assert res3.equals(res1)

    res4 = sentinel1.crop_burst_dataset(swath_ds, burst_id=365923)

    assert res4.equals(res1)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds, burst_index=8, azimuth_anx_time=2213)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds, burst_index=8, burst_id=365923)

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds, azimuth_anx_time=2213, burst_id=365923)

    with pytest.raises(IndexError):
        sentinel1.crop_burst_dataset(swath_ds, burst_index=-1)

    with pytest.raises(KeyError):
        sentinel1.crop_burst_dataset(swath_ds, burst_id=1)

    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")

    with pytest.raises(TypeError):
        sentinel1.crop_burst_dataset(swath_ds, burst_id=1)


def test_crop_burst_dataset_gcp() -> None:
    expected_geospatial_bounds = (
        "POLYGON((11.060741069073366 46.41270558692681,"
        "11.010711557932021 46.228050403919134,12.175715782110206 46.076023778486665,"
        "12.209682909257705 46.26327129178887,11.060741069073366 46.41270558692681))"
    )
    expected_polygon = shapely.wkt.loads(expected_geospatial_bounds)
    expected_geospatial_bbox = (
        11.010711557932021,
        46.076023778486665,
        12.209682909257705,
        46.41270558692681,
    )

    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV")
    gcp_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV/gcp")

    res = sentinel1.crop_burst_dataset(swath_ds, burst_index=5, gcp=gcp_ds)

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert res.dims["azimuth_time"] == swath_ds.attrs["lines_per_burst"]
    assert isinstance(res.attrs["geospatial_bounds"], str)
    assert shapely.wkt.loads(res.attrs["geospatial_bounds"]).is_valid
    assert shapely.wkt.loads(res.attrs["geospatial_bounds"]).equals(expected_polygon)
    assert res.attrs["geospatial_bounds"] == expected_geospatial_bounds
    geospatial_bbox = (
        res.attrs["geospatial_lon_min"],
        res.attrs["geospatial_lat_min"],
        res.attrs["geospatial_lon_max"],
        res.attrs["geospatial_lat_max"],
    )
    assert np.allclose(geospatial_bbox, expected_geospatial_bbox)


def test_mosaic_slc_iw() -> None:
    ds = sentinel1.open_sentinel1_dataset(SLC_IW_V340, group="IW1/HH")

    res = sentinel1.mosaic_slc_iw(ds)

    assert isinstance(res, xr.Dataset)

    res = sentinel1.mosaic_slc_iw(ds.measurement)

    assert isinstance(res, xr.DataArray)


def test_calibrate_amplitude() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")
    burst_ds = sentinel1.crop_burst_dataset(swath_ds, burst_index=8)
    cal_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH/calibration")

    res = sentinel1.calibrate_amplitude(burst_ds.measurement, cal_ds["betaNought"])

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.complex64)

    res = sentinel1.calibrate_amplitude(burst_ds.measurement, cal_ds["gamma"])

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.complex64)


def test_calibrate_intensity() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH")
    burst_ds = sentinel1.crop_burst_dataset(swath_ds, burst_index=8)
    cal_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VH/calibration")

    res = sentinel1.calibrate_intensity(burst_ds.measurement, cal_ds["betaNought"])

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.float32)

    cal_ds["betaNought"].attrs.pop("long_name")

    res = sentinel1.calibrate_intensity(
        burst_ds.measurement, cal_ds["betaNought"], as_db=True
    )

    assert set(res.dims) == {"azimuth_time", "slant_range_time"}
    assert np.issubdtype(res.dtype, np.float32)

    res = sentinel1.calibrate_intensity(
        burst_ds.measurement,
        cal_ds["betaNought"],
        as_db=True,
        min_db=None,
    )

    assert np.issubdtype(res.dtype, np.float32)


def test_slant_range_time_to_ground_range() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(SLC_IW, group="IW1/VV")
    swath = swath_ds.measurement[:1000, :1000]
    cc_ds = sentinel1.open_sentinel1_dataset(
        GRD_IW, group="IW/VV/coordinate_conversion"
    )

    res = sentinel1.slant_range_time_to_ground_range(
        swath.azimuth_time, swath.slant_range_time, cc_ds
    )

    assert isinstance(res, xr.DataArray)


def test_ground_range_to_slant_range_time() -> None:
    swath_ds = sentinel1.open_sentinel1_dataset(GRD_IW, group="IW/VV")
    swath = swath_ds.measurement[:1000, :1000]
    cc_ds = sentinel1.open_sentinel1_dataset(
        GRD_IW, group="IW/VV/coordinate_conversion"
    )

    res = sentinel1.ground_range_to_slant_range_time(
        swath.azimuth_time, swath.ground_range, cc_ds
    )

    assert isinstance(res, xr.DataArray)


def test_do_override_product_files() -> None:
    template = "{dirname}/{prefix}{swath}-{polarization}{ext}"
    _, product_files = esa_safe.parse_manifest_sentinel1(SLC_S3 / "manifest.safe")

    res = sentinel1.do_override_product_files(template, product_files)

    assert "./annotation/s3-vv.xml" in res
