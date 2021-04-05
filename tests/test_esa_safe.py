import pathlib
import typing as T

import pytest

from xarray_sentinel import esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SENTINEL1_ATTRIBUTES = {
    "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4": {
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
    },
    "S1A_S6_SLC__1SDV_20210402T115512_20210402T115535_037271_046407_39FD": {
        "constellation": "sentinel-1",
        "platform": "sentinel-1a",
        "instrument": ["c-sar"],
        "sat:orbit_state": "descending",
        "sat:absolute_orbit": 37271,
        "sat:relative_orbit": 99,
        "sat:anx_datetime": "2021-04-02T11:17:22.132050Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": "SM",
        "sar:polarizations": ["VV", "VH"],
        "sar:product_type": "SLC",
        "xs:instrument_mode_swaths": ["S6"],
    },
    "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001": {
        "constellation": "sentinel-1",
        "platform": "sentinel-1a",
        "instrument": ["c-sar"],
        "sat:orbit_state": "ascending",
        "sat:absolute_orbit": 37258,
        "sat:relative_orbit": 86,
        "sat:anx_datetime": "2021-04-01T13:53:42.874198Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": "SM",
        "sar:polarizations": ["VV", "VH"],
        "sar:product_type": "SLC",
        "xs:instrument_mode_swaths": ["S3"],
    },
    "S1A_EW_SLC__1SDH_20210403T122536_20210403T122630_037286_046484_8152": {
        "constellation": "sentinel-1",
        "platform": "sentinel-1a",
        "instrument": ["c-sar"],
        "sat:orbit_state": "descending",
        "sat:absolute_orbit": 37286,
        "sat:relative_orbit": 114,
        "sat:anx_datetime": "2021-04-03T11:58:30.792178Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": "EW",
        "sar:polarizations": ["HH", "HV"],
        "sar:product_type": "SLC",
        "xs:instrument_mode_swaths": ["EW1", "EW2", "EW3", "EW4", "EW5"],
    },
    "S1B_WV_SLC__1SSV_20210403T083025_20210403T084452_026300_032390_D542": {
        "constellation": "sentinel-1",
        "instrument": ["c-sar"],
        "platform": "sentinel-1b",
        "sar:frequency_band": "C",
        "sar:instrument_mode": "WV",
        "sar:polarizations": ["VV"],
        "sar:product_type": "SLC",
        "sat:absolute_orbit": 26300,
        "sat:anx_datetime": "2021-04-03T07:50:57.437371Z",
        "sat:orbit_state": "descending",
        "sat:relative_orbit": 24,
        "xs:instrument_mode_swaths": ["WV1", "WV2"],
    },
    "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8": {
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
        "sar:product_type": "GRD",
        "xs:instrument_mode_swaths": ["IW"],
    },
}

SENTINEL2_ATTRIBUTES = {
    "S2A_MSIL1C_20210403T101021_N0300_R022_T33TUM_20210403T110551": {
        "constellation": "sentinel-2",
        "platform": "sentinel-2a",
        "instrument": ["msi"],
        "sat:orbit_state": "descending",
        "sat:absolute_orbit": 30192,
        "sat:relative_orbit": 22,
        "xs:product_type": "S2MSIl1C",
    },
}


@pytest.mark.parametrize("product_id,expected", SENTINEL1_ATTRIBUTES.items())
def test_parse_manifest_sentinel1(
    product_id: str, expected: T.Dict[str, T.Any]
) -> None:
    product_folder = DATA_FOLDER / (product_id + ".SAFE")
    manifest = esa_safe.open_manifest(product_folder)

    res_attrs, res_files = esa_safe.parse_manifest_sentinel1(manifest)

    assert res_attrs == expected


@pytest.mark.parametrize("product_id,expected", SENTINEL2_ATTRIBUTES.items())
def test_parse_manifest_sentinel2(
    product_id: str, expected: T.Dict[str, T.Any]
) -> None:
    product_folder = DATA_FOLDER / (product_id + ".SAFE")
    manifest = esa_safe.open_manifest(product_folder)

    res_attrs, res_files = esa_safe.parse_manifest_sentinel2(manifest)

    assert res_attrs == expected
