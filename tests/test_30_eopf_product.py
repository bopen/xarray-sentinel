import json
import pathlib
import warnings
from typing import Any

import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import eopf_product

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)
SLC_S3 = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
)
GRD_IW_2 = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20211223T051122_20211223T051147_030148_039993_5371.SAFE"
)
SLC_IW_V340 = (
    DATA_FOLDER
    / "S1A_IW_SLC__1SDH_20220414T102209_20220414T102236_042768_051AA4_E677.SAFE"
)
SLC_IW_NODE = "S01SIWSLC_20210401T052622_0028_B150_EFA4_032297_IW1_0"
# the CPM 3.0 burst node with our deliberate differences, see docs/DATATREE.md
EXPECTED_SLC_IW_STRUCTURE = json.loads(
    (DATA_FOLDER / "eopf" / "S01SIWSLC_target.json").read_text()
)
EXPECTED_SLC_IW_ATTRS = json.loads(
    (DATA_FOLDER / "eopf" / "S01SIWSLC_target_attrs.json").read_text()
)


def datatree_structure(dt: xr.DataTree) -> dict[str, dict[str, list[Any]]]:
    return {
        node.relative_to(dt): {
            str(name): [list(var.dims), str(var.dtype)]
            for name, var in node.to_dataset(inherit=False).variables.items()
        }
        for node in dt.subtree
    }


def attrs_structure(value: Any, target: Any) -> Any:
    if not (isinstance(value, dict) and isinstance(target, dict)):
        return type(value).__name__
    structure = {}
    for key, item in value.items():
        structure[key] = attrs_structure(item, target.get(key))
    return structure


S3_SAFE_NAME = "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001"
S3_COMMON_ATTRS = {
    "family_name": "SENTINEL-1",
    "number": "A",
    "mode": "SM",
    "swaths": ["S3"],
    "orbit_number": 37258,
    "mission_data_take_id": "287630",
    "product_type": "SLC",
    "start_time": "2021-04-01T15:28:55.1",
    "stop_time": "2021-04-01T15:29:14.9",
}


@pytest.mark.parametrize(
    "safe_name,common_attrs,expected",
    [
        [
            "S1C_IW_SLC__1SDV_20260731T234807_20260731T234821_008794_0116E8_C079",
            {
                "family_name": "SENTINEL-1",
                "number": "C",
                "mode": "IW",
                "swaths": ["IW1", "IW2", "IW3"],
                "orbit_number": 8794,
                "mission_data_take_id": "71400",
                "product_type": "SLC",
                "start_time": "2026-07-31T23:48:07.875379",
                "stop_time": "2026-07-31T23:48:21.123456",
            },
            "S01SIWSLC_20260731T234807_0014_C050_C079_0116E8",
        ],
        [
            "S1C_IW_SLC__1SDH_20260531T194042_20260531T194109_007902_01011D_EC26",
            {
                "family_name": "SENTINEL-1",
                "number": "C",
                "mode": "IW",
                "swaths": ["IW1", "IW2", "IW3"],
                "orbit_number": 7902,
                "mission_data_take_id": "65821",
                "product_type": "SLC",
                "start_time": "2026-05-31T19:40:42.5",
                "stop_time": "2026-05-31T19:41:09.5",
            },
            "S01SIWSLC_20260531T194042_0027_C045_EC26_01011D",
        ],
        [
            "S1C_IW_GRDH_1SDV_20261017T111256_20261017T111323_009924_013C8F_ECF5",
            {
                "family_name": "SENTINEL-1",
                "number": "C",
                "mode": "IW",
                "swaths": ["IW"],
                "orbit_number": 9924,
                "mission_data_take_id": "81039",
                "product_type": "GRD",
                "start_time": "2026-10-17T11:12:56.1",
                "stop_time": "2026-10-17T11:13:23.9",
            },
            "S01SIWGRD_20261017T111256_0027_C057_ECF5_013C8F",
        ],
        [
            "S1D_IW_GRDH_1SDV_20261023T173456_20261023T173521_005145_009C11_F2F3_COG",
            {
                "family_name": "SENTINEL-1",
                "number": "D",
                "mode": "IW",
                "swaths": ["IW"],
                "orbit_number": 5145,
                "mission_data_take_id": "39953",
                "product_type": "GRD",
                "start_time": "2026-10-23T17:34:56.1",
                "stop_time": "2026-10-23T17:35:21.9",
            },
            "S01SIWGRD_20261023T173456_0025_D029_F2F3_009C11",
        ],
        [
            S3_SAFE_NAME,
            S3_COMMON_ATTRS,
            "S01SS3SLC_20210401T152855_0019_A213_6001_04638E",
        ],
    ],
)
def test_make_product_name(
    safe_name: str, common_attrs: dict[str, Any], expected: str
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        product_name = eopf_product.make_product_name(safe_name, common_attrs)

    assert product_name == expected


def test_make_product_name_mismatch() -> None:
    common_attrs = S3_COMMON_ATTRS | {"number": "B"}

    with pytest.warns(UserWarning, match="differs from the manifest"):
        product_name = eopf_product.make_product_name(S3_SAFE_NAME, common_attrs)

    assert product_name == "S01SS3SLC_20210401T152855_0019_B213_6001_04638E"


def test_make_product_name_duration() -> None:
    # the duration of the SAFE name wins over the manifest one
    common_attrs = S3_COMMON_ATTRS | {"stop_time": "2021-04-01T15:29:44.9"}

    with pytest.warns(UserWarning, match="differs from the manifest"):
        product_name = eopf_product.make_product_name(S3_SAFE_NAME, common_attrs)

    assert product_name == "S01SS3SLC_20210401T152855_0019_A213_6001_04638E"


def test_make_product_name_unparsable() -> None:
    with pytest.warns(UserWarning, match="cannot parse SAFE name"):
        product_name = eopf_product.make_product_name(
            "S1A_S3_SLC_1SDV", S3_COMMON_ATTRS
        )

    assert product_name == "S01SS3SLC_20210401T152855_0019_A213_UNKN_04638E"


def test_open_datatree_grd() -> None:
    res = eopf_product.open_datatree(GRD_IW_2, check_files_exist=True)

    assert list(res.children) == ["S01SIWGRD_20211223T051122_0025_B172_5371_039993"]

    node = res["S01SIWGRD_20211223T051122_0025_B172_5371_039993"]

    assert "coordinate_conversion" in node["conditions"].children
    assert node["measurements/grd"].dims == (
        "polarization",
        "azimuth_time",
        "ground_range",
    )
    for group in ["conditions/gcp", "quality/calibration", "quality/noise_range"]:
        assert "ground_range" in node[group].dims


def test_open_datatree_grd_encoding(tmp_path: pathlib.Path) -> None:
    res = eopf_product.open_datatree(GRD_IW_2, check_files_exist=True)
    node = res["S01SIWGRD_20211223T051122_0025_B172_5371_039993"]
    measurements = node["measurements"].to_dataset()
    grd = measurements.grd.isel(azimuth_time=slice(2), ground_range=slice(3)).load()
    assert grd.dtype == "uint16"
    grd[0, 0, 0] = 65535

    grd.to_dataset().to_zarr(tmp_path / "grd.zarr", consolidated=False)

    raw = xr.open_zarr(tmp_path / "grd.zarr", consolidated=False, mask_and_scale=False)
    assert raw.grd.dtype == "uint16"
    np.testing.assert_array_equal(raw.grd.values, grd.values)
    decoded = xr.open_zarr(tmp_path / "grd.zarr", consolidated=False)
    assert decoded.grd.dtype == "float32"
    assert decoded.grd.values[0, 0, 0] == 65535
    xr.testing.assert_equal(decoded.grd, grd.astype("float32").where(grd != 0))


@pytest.fixture(scope="module")
def slc_iw_node_structure() -> dict[str, dict[str, list[Any]]]:
    dt = eopf_product.open_datatree(SLC_IW, check_files_exist=True)
    return datatree_structure(dt.children[SLC_IW_NODE])


def test_open_datatree(capsys: pytest.CaptureFixture[str]) -> None:
    res = eopf_product.open_datatree(SLC_S3, check_files_exist=True)

    assert isinstance(res, xr.DataTree)
    assert list(res.children) == ["S01SS3SLC_20210401T152855_0019_A213_6001_04638E"]
    assert capsys.readouterr().out == ""


def test_open_datatree_bursts() -> None:
    res = eopf_product.open_datatree(SLC_IW, check_files_exist=True)

    assert len(res.children) == 19

    node = res[SLC_IW_NODE]
    slc = node["measurements/slc"]

    assert node.attrs["other_metadata"].keys() == {"VH", "VV"}
    assert isinstance(slc, xr.DataArray)
    assert slc.dims == ("polarization", "azimuth_time", "slant_range_time")
    assert slc.polarization.values.tolist() == ["VH", "VV"]
    assert slc.attrs == {"long_name": "digital number"}
    assert slc.chunks is not None
    assert {d: c[0] for d, c in zip(slc.dims, slc.chunks)} == {
        "polarization": 1,
        "azimuth_time": slc.sizes["azimuth_time"],
        "slant_range_time": 4096,
    }
    assert node["quality/calibration"].sizes["polarization"] == 2
    assert "polarization" not in node["conditions/orbit"].dims


def test_open_datatree_groups(
    slc_iw_node_structure: dict[str, dict[str, list[Any]]],
) -> None:
    assert slc_iw_node_structure.keys() == EXPECTED_SLC_IW_STRUCTURE.keys()


@pytest.mark.parametrize("group", sorted(EXPECTED_SLC_IW_STRUCTURE))
def test_open_datatree_group_structure(
    slc_iw_node_structure: dict[str, dict[str, list[Any]]], group: str
) -> None:
    assert slc_iw_node_structure.get(group) == EXPECTED_SLC_IW_STRUCTURE[group]


def test_open_datatree_attrs() -> None:
    res = eopf_product.open_datatree(SLC_IW_V340, check_files_exist=True)
    node = res.children["S01SIWSLC_20220414T102209_0027_A244_E677_051AA4_IW1_365915"]
    stac_discovery = node.attrs["stac_discovery"]
    root_stac_discovery = res.attrs["stac_discovery"]

    assert res.attrs["other_metadata"] == {
        "eopf_category": "eocontainer",
        "title": "S01SIWSLC",
    }
    assert (
        root_stac_discovery["id"] == "S01SIWSLC_20220414T102209_0027_A244_E677_051AA4"
    )
    assert root_stac_discovery["assets"] == {}
    assert "sar:relative_burst" not in root_stac_discovery["properties"]
    assert list(node.attrs["other_metadata"]) == ["HH"]

    # other_metadata of one polarisation
    node_attrs = dict(node.attrs) | {
        "other_metadata": node.attrs["other_metadata"]["HH"]
    }

    assert attrs_structure(node_attrs, EXPECTED_SLC_IW_ATTRS) == EXPECTED_SLC_IW_ATTRS
    assert stac_discovery["id"] == node.name
    assert stac_discovery["properties"]["sar:relative_burst"] == 365915
