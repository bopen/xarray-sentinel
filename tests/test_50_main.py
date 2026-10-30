import json
import pathlib
from typing import Any

import pytest
import xarray as xr
from typer.testing import CliRunner

from xarray_sentinel import __main__

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

GRD_IW = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20211223T051122_20211223T051147_030148_039993_5371.SAFE"
)
GRD_IW_NODE = "S01SIWGRD_20211223T051122_0025_B172_5371_039993"
SLC_WV = (
    DATA_FOLDER
    / "S1B_WV_SLC__1SSV_20210403T083025_20210403T084452_026300_032390_D542.SAFE"
)

runner = CliRunner()


def test_version() -> None:
    res = runner.invoke(__main__.app, ["--version"])

    assert res.exit_code == 0
    assert res.stdout.startswith("xarray-sentinel, version ")


def test_help() -> None:
    res = runner.invoke(__main__.app, [])

    assert "convert" in res.output
    assert "info" in res.output


def test_info() -> None:
    res = runner.invoke(__main__.app, ["info", str(GRD_IW)])

    assert res.exit_code == 0
    assert json.loads(res.stdout)["id"] == GRD_IW_NODE

    # the WV test product has only the manifest
    res = runner.invoke(__main__.app, ["info", str(SLC_WV)])

    assert res.exit_code == 0
    assert json.loads(res.stdout)["properties"]["sar:instrument_mode"] == "WV"


def test_convert(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    open_datatree = xr.open_datatree

    # the test products miss some files and the command has no option to skip them
    def open_available_files(*args: Any, **kwargs: Any) -> xr.DataTree:
        return open_datatree(*args, check_files_exist=True, **kwargs)

    monkeypatch.setattr(xr, "open_datatree", open_available_files)
    target = tmp_path / "product.zarr"

    res = runner.invoke(__main__.app, ["convert", str(GRD_IW), str(target)])

    assert res.exit_code == 0
    # consolidated=True fails if the metadata are not consolidated
    datatree = open_datatree(target, engine="zarr", consolidated=True, chunks={})
    assert list(datatree.children) == [GRD_IW_NODE]
    grd = datatree[GRD_IW_NODE]["measurements"]["grd"]
    assert grd.dtype == "float32"
    assert grd.encoding["preferred_chunks"]["ground_range"] == 4096
    assert grd.encoding["preferred_chunks"]["azimuth_time"] == 4096


def test_convert_wv(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "product.zarr"

    res = runner.invoke(__main__.app, ["convert", str(SLC_WV), str(target)])

    assert res.exit_code != 0
    assert isinstance(res.exception, ValueError)
    assert not target.exists()
