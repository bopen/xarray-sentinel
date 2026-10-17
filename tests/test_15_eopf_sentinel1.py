import pathlib

import xarray as xr

from xarray_sentinel import eopf_sentinel1, esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW1_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
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
