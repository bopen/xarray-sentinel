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
GRD_IW_2 = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20211223T051122_20211223T051147_030148_039993_5371.SAFE"
)
GRD_IW_2_VV_annotation = (
    GRD_IW_2
    / "annotation"
    / "s1b-iw-grd-vv-20211223t051122-20211223t051147-030148-039993-001.xml"
)
GRD_IW_2_VV_noise = (
    GRD_IW_2
    / "annotation"
    / "calibration"
    / "noise-s1b-iw-grd-vv-20211223t051122-20211223t051147-030148-039993-001.xml"
)
GRD_IW_3 = (
    DATA_FOLDER
    / "S1C_IW_GRDH_1SDH_20261001T085007_20261001T085036_009689_0134B6_D9A1.SAFE"
)
# trimmed to the first antenna pattern of each sub-swath
GRD_IW_3_HH_annotation = (
    GRD_IW_3
    / "annotation"
    / "s1c-iw-grd-hh-20261001t085007-20261001t085036-009689-0134b6-001.xml"
)
# trimmed to the noise range vectors 0, 2 and 3, one per pixel pattern
GRD_IW_3_HH_noise = (
    GRD_IW_3_HH_annotation.parent
    / "calibration"
    / "noise-s1c-iw-grd-hh-20261001t085007-20261001t085036-009689-0134b6-001.xml"
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
    np.testing.assert_allclose(
        res.slant_range_time.values,
        res.slant_range_time_gcp.isel(azimuth_time=0).values,
        rtol=1e-12,
    )

    res = eopf_sentinel1.open_gcp(esa_safe.parse_xml(GRD_IW_VV_annotation))

    assert res.latitude.dims == ("azimuth_time", "ground_range")
    assert res.slant_range_time_gcp.dims == ("azimuth_time", "ground_range")


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
    assert res.pixel.dims == ("slant_range_time",)

    res = eopf_sentinel1.open_noise_range(
        esa_safe.parse_xml(GRD_IW_2_VV_noise, "noise"),
        esa_safe.parse_xml(GRD_IW_2_VV_annotation),
    )

    assert dict(res.sizes) == {"azimuth_time": 27, "ground_range": 657}
    assert res.pixel.dims == ("azimuth_time", "ground_range")
    assert (res.pixel.values >= 0).all()

    res = eopf_sentinel1.open_noise_range(
        esa_safe.parse_xml(GRD_IW_3_HH_noise, "noise"),
        esa_safe.parse_xml(GRD_IW_3_HH_annotation),
    )

    assert dict(res.sizes) == {"azimuth_time": 3, "ground_range": 644}
    assert res.pixel.dims == ("azimuth_time", "ground_range")
    assert res.pixel.values[:, 221].tolist() == [8840, 8808, 8808]
    assert res.pixel.values[:, -1].tolist() == [-1, 25567, 25567]
    assert np.isnan(res.noise_range_lut.values[0, -1])


def test_azimuth_time_coordinate() -> None:
    annotation = esa_safe.parse_xml(SLC_IW1_VV_annotation)
    swath_timing = esa_safe.get_tag(annotation, "swathTiming")
    bursts = swath_timing["burstList"]["burst"]
    line = np.array([0, swath_timing["linesPerBurst"]])

    res = eopf_sentinel1.azimuth_time_coordinate(line, annotation)

    expected = [np.datetime64(b["azimuthTime"], "ns") for b in bursts[:2]]
    np.testing.assert_array_equal(res, expected)

    annotation = esa_safe.parse_xml(GRD_IW_VV_annotation)
    image_information = esa_safe.get_tag(annotation, "imageAnnotation/imageInformation")
    line = np.array([0, image_information["numberOfLines"] - 1])

    res = eopf_sentinel1.azimuth_time_coordinate(line, annotation)

    expected = [
        np.datetime64(image_information["productFirstLineUtcTime"], "ns"),
        np.datetime64(image_information["productLastLineUtcTime"], "ns"),
    ]
    np.testing.assert_array_equal(res, expected)


def test_open_noise_azimuth() -> None:
    res = eopf_sentinel1.open_noise_azimuth(
        esa_safe.parse_xml(SLC_IW1_VV_noise, "noise"),
        esa_safe.parse_xml(SLC_IW1_VV_annotation),
    )

    assert res.noise_azimuth_lut.dims == ("azimuth_time", "swath")
    assert res.noise_azimuth_lut.dtype == "float32"
    assert res.swath.values.tolist() == ["IW1"]
    assert res.line.dims == ("azimuth_time",)

    res = eopf_sentinel1.open_noise_azimuth(
        esa_safe.parse_xml(GRD_IW_2_VV_noise, "noise"),
        esa_safe.parse_xml(GRD_IW_2_VV_annotation),
    )

    assert res.swath.values.tolist() == ["IW1", "IW2", "IW3"]
    assert res.first_range_sample.values.tolist() == [0, 8890, 17701]
    assert res.noise_azimuth_lut.count("azimuth_time").values.tolist() == [
        1689,
        1688,
        1686,
    ]
    assert res.indexes["azimuth_time"].is_monotonic_increasing
