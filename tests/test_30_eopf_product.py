import json
import pathlib
from typing import Any

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


@pytest.mark.parametrize(
    "safe_name,expected",
    [
        [
            "S1C_IW_SLC__1SDV_20260731T234807_20260731T234821_008794_0116E8_C079",
            "S01SIWSLC_20260731T234807_0014_C050_C079_0116E8",
        ],
        [
            "S1C_IW_SLC__1SDH_20260531T194042_20260531T194109_007902_01011D_EC26",
            "S01SIWSLC_20260531T194042_0027_C045_EC26_01011D",
        ],
        [
            "S1C_IW_GRDH_1SDV_20261017T111256_20261017T111323_009924_013C8F_ECF5",
            "S01SIWGRD_20261017T111256_0027_C057_ECF5_013C8F",
        ],
    ],
)
def test_make_product_name(safe_name: str, expected: str) -> None:
    assert eopf_product.make_product_name(safe_name) == expected


def test_make_product_name_error() -> None:
    with pytest.raises(ValueError):
        eopf_product.make_product_name("S2A_MSIL1C_20210403T101021_N0300_R022_T33TUM")


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

    assert res.attrs == {
        "other_metadata": {"eopf_category": "eocontainer", "title": "S01SIWSLC"}
    }
    assert list(node.attrs["other_metadata"]) == ["HH"]

    # other_metadata of one polarisation
    node_attrs = dict(node.attrs) | {
        "other_metadata": node.attrs["other_metadata"]["HH"]
    }

    assert attrs_structure(node_attrs, EXPECTED_SLC_IW_ATTRS) == EXPECTED_SLC_IW_ATTRS
    assert stac_discovery["id"] == node.name
    assert stac_discovery["properties"]["sar:relative_burst"] == 365915
