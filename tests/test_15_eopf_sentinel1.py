import pathlib

import numpy as np
import xarray as xr

from xarray_sentinel import eopf_sentinel1, esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW1_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_calibration = (
    SLC_IW1_VV_annotation.parent
    / "calibration"
    / "calibration-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_noise = (
    SLC_IW1_VV_annotation.parent
    / "calibration"
    / "noise-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
GRD_IW_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_open_antenna_pattern() -> None:
    res = eopf_sentinel1.open_antenna_pattern(esa_safe.parse_xml(GRD_IW_VV_annotation))

    assert dict(res.sizes) == {"azimuth_time": 27, "count": 679}
    assert set(res.swath.values.tolist()) == {"IW1", "IW2", "IW3"}
    assert res.slant_range_time_ap.count("count").values.min() == 563


def test_open_attitude() -> None:
    res = eopf_sentinel1.open_attitude(esa_safe.parse_xml(SLC_IW1_VV_annotation))

    assert dict(res.sizes) == {"azimuth_time": 25}
    assert {str(var.dtype) for var in res.data_vars.values()} == {"float32"}


def test_open_orbit() -> None:
    res = eopf_sentinel1.open_orbit(esa_safe.parse_xml(SLC_IW1_VV_annotation))

    assert res.position.dims == ("azimuth_time", "axis")
    assert res.axis.values.tolist() == ["x", "y", "z"]
    assert res.attrs == {"reference_system": "Earth Fixed"}


def test_open_doppler_centroid() -> None:
    res = eopf_sentinel1.open_doppler_centroid(
        esa_safe.parse_xml(SLC_IW1_VV_annotation)
    )

    assert res.degree.values.tolist() == [0, 1, 2]
    assert res.data_dc_polynomial.dtype == "float32"
    assert res.fine_dce_azimuth_start_time.dtype == "datetime64[ns]"
    assert res.data_dc_rms_error_above_threshold.dtype == bool


def test_open_coordinate_conversion() -> None:
    # dims and dtypes from the CPM 3.0 S01SIWGRD mapping
    expected = {
        "azimuth_time": [["azimuth_time"], "datetime64[ns]"],
        "degree": [["degree"], "int64"],
        "gr0": [["azimuth_time"], "float64"],
        "grsr_coefficients": [["azimuth_time", "degree"], "float64"],
        "slant_range_time": [["azimuth_time"], "float64"],
        "sr0": [["azimuth_time"], "float64"],
        "srgr_coefficients": [["azimuth_time", "degree"], "float64"],
    }

    res = eopf_sentinel1.open_coordinate_conversion(
        esa_safe.parse_xml(GRD_IW_VV_annotation)
    )

    assert isinstance(res, xr.Dataset)
    assert {
        str(name): [list(var.dims), str(var.dtype)]
        for name, var in res.variables.items()
    } == expected

    res = eopf_sentinel1.open_coordinate_conversion(
        esa_safe.parse_xml(SLC_IW1_VV_annotation)
    )

    assert res is None


def test_open_gcp() -> None:
    res = eopf_sentinel1.open_gcp(esa_safe.parse_xml(SLC_IW1_VV_annotation))

    assert dict(res.sizes) == {"azimuth_time": 10, "slant_range_time": 21}
    assert res.azimuth_time_gcp.dtype == "datetime64[ns]"
    assert (res.azimuth_time == res.azimuth_time_gcp.isel(slant_range_time=0)).all()
    assert (res.slant_range_time == res.slant_range_time_gcp.isel(azimuth_time=0)).all()


def test_range_coordinate() -> None:
    pixel = np.array([0, 10])
    annotation = esa_safe.parse_xml(SLC_IW1_VV_annotation)
    image_information = esa_safe.get_tag(annotation, "imageAnnotation/imageInformation")

    name, values = eopf_sentinel1.range_coordinate(pixel, annotation)

    assert name == "slant_range_time"
    assert values[0] == image_information["slantRangeTime"]

    name, values = eopf_sentinel1.range_coordinate(
        pixel, esa_safe.parse_xml(GRD_IW_VV_annotation)
    )

    assert name == "ground_range"
    assert values.tolist() == [0.0, 100.0]


def test_open_calibration() -> None:
    res = eopf_sentinel1.open_calibration(
        esa_safe.parse_xml(SLC_IW1_VV_calibration, "calibration"),
        esa_safe.parse_xml(SLC_IW1_VV_annotation),
    )

    assert res.sigma_nought.dims == ("azimuth_time", "slant_range_time")
    assert res.sigma_nought.dtype == "float32"
    assert res.pixel.dims == ("slant_range_time",)
    assert res.attrs == {"absolute_calibration_constant": 1.393}


def test_open_noise_range() -> None:
    res = eopf_sentinel1.open_noise_range(
        esa_safe.parse_xml(SLC_IW1_VV_noise, "noise"),
        esa_safe.parse_xml(SLC_IW1_VV_annotation),
    )

    assert dict(res.sizes) == {"azimuth_time": 10, "slant_range_time": 542}
    assert res.noise_range_lut.dtype == "float32"
