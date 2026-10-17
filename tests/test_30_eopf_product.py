import pathlib

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
