import pathlib
from typing import Any, Dict
from xml.etree import ElementTree

import pytest
import xmlschema

from xarray_sentinel import esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SENTINEL1_ATTRIBUTES = {
    "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4": {
        "ascending_node_time": "2021-04-01T04:49:55.637823",
        "family_name": "SENTINEL-1",
        "mode": "IW",
        "number": "B",
        "orbit_number": 26269,
        "pass": "DESCENDING",
        "product_type": "SLC",
        "relative_orbit_number": 168,
        "start_time": "2021-04-01T05:26:22.396989",
        "stop_time": "2021-04-01T05:26:50.325833",
        "swaths": ["IW1", "IW2", "IW3"],
        "transmitter_receiver_polarisations": ["VV", "VH"],
    },
    "S1A_S6_SLC__1SDV_20210402T115512_20210402T115535_037271_046407_39FD": {
        "ascending_node_time": "2021-04-02T11:17:22.132050",
        "family_name": "SENTINEL-1",
        "mode": "SM",
        "number": "A",
        "orbit_number": 37271,
        "pass": "DESCENDING",
        "product_type": "SLC",
        "relative_orbit_number": 99,
        "start_time": "2021-04-02T11:55:12.030410",
        "stop_time": "2021-04-02T11:55:35.706705",
        "swaths": ["S6"],
        "transmitter_receiver_polarisations": ["VV", "VH"],
    },
    "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001": {
        "ascending_node_time": "2021-04-01T13:53:42.874198",
        "family_name": "SENTINEL-1",
        "mode": "SM",
        "number": "A",
        "orbit_number": 37258,
        "pass": "ASCENDING",
        "product_type": "SLC",
        "relative_orbit_number": 86,
        "start_time": "2021-04-01T15:28:55.111501",
        "stop_time": "2021-04-01T15:29:14.277650",
        "swaths": ["S3"],
        "transmitter_receiver_polarisations": ["VV", "VH"],
    },
    "S1A_EW_SLC__1SDH_20210403T122536_20210403T122630_037286_046484_8152": {
        "ascending_node_time": "2021-04-03T11:58:30.792178",
        "family_name": "SENTINEL-1",
        "mode": "EW",
        "number": "A",
        "orbit_number": 37286,
        "pass": "DESCENDING",
        "product_type": "SLC",
        "relative_orbit_number": 114,
        "start_time": "2021-04-03T12:25:36.505937",
        "stop_time": "2021-04-03T12:26:30.902216",
        "swaths": ["EW1", "EW2", "EW3", "EW4", "EW5"],
        "transmitter_receiver_polarisations": ["HH", "HV"],
    },
    "S1B_WV_SLC__1SSV_20210403T083025_20210403T084452_026300_032390_D542": {
        "ascending_node_time": "2021-04-03T07:50:57.437371",
        "family_name": "SENTINEL-1",
        "mode": "WV",
        "number": "B",
        "orbit_number": 26300,
        "pass": "DESCENDING",
        "product_type": "SLC",
        "relative_orbit_number": 24,
        "start_time": "2021-04-03T08:30:25.749829",
        "stop_time": "2021-04-03T08:44:52.841818",
        "swaths": ["WV1", "WV2"],
        "transmitter_receiver_polarisations": ["VV"],
    },
    "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8": {
        "ascending_node_time": "2021-04-01T04:49:55.637823",
        "family_name": "SENTINEL-1",
        "mode": "IW",
        "number": "B",
        "orbit_number": 26269,
        "pass": "DESCENDING",
        "product_type": "GRD",
        "relative_orbit_number": 168,
        "start_time": "2021-04-01T05:26:23.794457",
        "stop_time": "2021-04-01T05:26:48.793373",
        "swaths": ["IW"],
        "transmitter_receiver_polarisations": ["VV", "VH"],
    },
}

ANNOTATION_PATH = str(
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)


def test_cached_sentinel1_schemas() -> None:
    res = esa_safe.cached_sentinel1_schemas("annotation")

    assert isinstance(res, xmlschema.XMLSchema)


def test_parse_tag() -> None:
    expected = {
        "timelinessCategory",
        "platformHeading",
        "radarFrequency",
        "rangeSamplingRate",
        "projection",
        "pass",
        "azimuthSteeringRate",
    }

    res = esa_safe.parse_tag(ANNOTATION_PATH, ".//productInformation")

    assert isinstance(res, dict)
    assert set(res) == expected


def test_parse_tag_as_list() -> None:
    expected = {
        "azimuthTime",
        "firstValidSample",
        "sensingTime",
        "lastValidSample",
        "byteOffset",
        "azimuthAnxTime",
    }

    res = esa_safe.parse_tag_as_list(ANNOTATION_PATH, ".//burst")

    assert isinstance(res, list)
    assert set(res[0]) == expected

    # XPath to a single element
    res = esa_safe.parse_tag_as_list(ANNOTATION_PATH, ".//burst[1]")

    assert isinstance(res, list)
    assert set(res[0]) == expected

    # XPath to a non existent element
    res = esa_safe.parse_tag_as_list(ANNOTATION_PATH, ".//dummy")

    assert isinstance(res, list)
    assert res == []


def test_parse_annotation_filename() -> None:
    res = esa_safe.parse_annotation_filename(
        "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
    )

    assert res == ("", "iw1", "vv", "20210401t052624")

    with pytest.raises(ValueError):
        esa_safe.parse_annotation_filename("")


def test_findtext() -> None:
    tree = ElementTree.fromstring("<root><child>text</child></root>")

    res = esa_safe.findtext(tree, ".//child")

    assert res == "text"

    with pytest.raises(ValueError):
        esa_safe.findtext(tree, ".//dummy")


def test_findall() -> None:
    tree = ElementTree.fromstring("<root><c1>text</c1><c2></c2></root>")

    res = esa_safe.findall(tree, ".//c1")

    assert res == ["text"]

    with pytest.raises(ValueError):
        esa_safe.findall(tree, ".//c2")


@pytest.mark.parametrize("product_id,expected", SENTINEL1_ATTRIBUTES.items())
def test_parse_manifest_sentinel1(product_id: str, expected: Dict[str, Any]) -> None:
    manifest_path = DATA_FOLDER / (product_id + ".SAFE") / "manifest.safe"

    res_attrs, res_files = esa_safe.parse_manifest_sentinel1(manifest_path)

    assert res_attrs == expected


def test_make_stac_item() -> None:
    attrs = SENTINEL1_ATTRIBUTES[
        "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8"
    ]
    expected = {
        "constellation": "sentinel-1",
        "instrument": ["c-sar"],
        "platform": "sentinel-1b",
        "sat:orbit_state": "descending",
        "sat:absolute_orbit": 26269,
        "sat:relative_orbit": 168,
        "sat:anx_datetime": "2021-04-01T04:49:55.637823Z",
        "sar:instrument_mode": "IW",
        "sar:frequency_band": "C",
        "sar:polarizations": ["VV", "VH"],
        "sar:product_type": "GRD",
        "sar:observation_direction": "right",
    }

    assert esa_safe.make_stac_item(attrs) == expected
