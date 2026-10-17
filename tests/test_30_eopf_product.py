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
EOPF_SLC_IW_NODE = (
    DATA_FOLDER
    / "eopf"
    / "S01SIWSLC_20260731T234807_0014_C050_C079_0116E8_IW3_258176.json"
)

# EOPF quirks we fix, see docs/DATATREE.md
EOPF_FIXES = {
    "conditions/doppler_centroid": {
        "fine_dce_azimuth_start_time": [
            ["polarization", "azimuth_time"],
            "datetime64[ns]",
        ],
        "fine_dce_azimuth_stop_time": [
            ["polarization", "azimuth_time"],
            "datetime64[ns]",
        ],
    },
}
EXPECTED_SLC_IW_STRUCTURE = {
    group: variables | EOPF_FIXES.get(group, {})
    for group, variables in json.loads(EOPF_SLC_IW_NODE.read_text()).items()
}
PENDING = pytest.mark.xfail(strict=True, reason="EOPF converter not implemented yet")


def datatree_structure(dt: xr.DataTree) -> dict[str, dict[str, list[Any]]]:
    return {
        node.relative_to(dt): {
            str(name): [list(var.dims), str(var.dtype)]
            for name, var in node.to_dataset(inherit=False).variables.items()
        }
        for node in dt.subtree
    }


@pytest.fixture(scope="module")
def slc_iw_node_structure() -> dict[str, dict[str, list[Any]]]:
    dt = eopf_product.open_datatree(SLC_IW, check_files_exist=True)
    return datatree_structure(dt.children[f"{SLC_IW.stem}_IW1_0"])


def test_open_datatree(capsys: pytest.CaptureFixture[str]) -> None:
    res = eopf_product.open_datatree(SLC_S3, check_files_exist=True)

    assert isinstance(res, xr.DataTree)
    assert list(res.children) == [f"{SLC_S3.stem}_S3"]
    assert capsys.readouterr().out == ""


def test_open_datatree_bursts() -> None:
    res = eopf_product.open_datatree(SLC_IW, check_files_exist=True)

    assert len(res.children) == 19

    node = res[f"{SLC_IW.stem}_IW1_0"]
    slc = node["measurements/slc"]

    assert node.attrs["other_metadata"].keys() == {"VH", "VV"}
    assert isinstance(slc, xr.DataArray)
    assert slc.dims == ("polarization", "azimuth_time", "slant_range_time")
    assert slc.polarization.values.tolist() == ["VH", "VV"]
    assert node["quality/calibration"].sizes["polarization"] == 2
    assert "polarization" not in node["conditions/orbit"].dims


@PENDING
def test_open_datatree_groups(
    slc_iw_node_structure: dict[str, dict[str, list[Any]]],
) -> None:
    assert slc_iw_node_structure.keys() == EXPECTED_SLC_IW_STRUCTURE.keys()


@pytest.mark.parametrize(
    "group",
    [
        ".",
        "conditions",
        "quality",
        pytest.param("measurements", marks=PENDING),
        pytest.param("conditions/antenna_pattern", marks=PENDING),
        pytest.param("conditions/attitude", marks=PENDING),
        pytest.param("conditions/doppler_centroid", marks=PENDING),
        pytest.param("conditions/gcp", marks=PENDING),
        pytest.param("conditions/orbit", marks=PENDING),
        pytest.param("quality/calibration", marks=PENDING),
        pytest.param("quality/noise_azimuth", marks=PENDING),
        pytest.param("quality/noise_range", marks=PENDING),
    ],
)
def test_open_datatree_group_structure(
    slc_iw_node_structure: dict[str, dict[str, list[Any]]], group: str
) -> None:
    assert slc_iw_node_structure.get(group) == EXPECTED_SLC_IW_STRUCTURE[group]
