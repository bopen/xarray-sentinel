import pathlib
from typing import Any, Dict

import pytest
import xarray as xr
from cfchecker import cfchecks

pytest.importorskip("netCDF4")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def cfcheck(path: str) -> Dict[str, int]:
    (
        badc,
        coards,
        debug,
        uploader,
        useFileName,
        regionnames,
        standardName,
        areaTypes,
        cacheDir,
        cacheTables,
        cacheTime,
        version,
        files,
    ) = cfchecks.getargs(["cfchecks", path])

    inst = cfchecks.CFChecker(
        uploader=uploader,
        useFileName=useFileName,
        badc=badc,
        coards=coards,
        cfRegionNamesXML=regionnames,
        cfStandardNamesXML=standardName,
        cfAreaTypesXML=areaTypes,
        cacheDir=cacheDir,
        cacheTables=cacheTables,
        cacheTime=cacheTime,
        version=version,
        debug=debug,
    )
    for file in files:
        try:
            inst.checker(file)
        except cfchecks.FatalCheckerError:
            print("Checking of file %s aborted due to error" % file)

    totals: Dict[str, int] = inst.get_total_counts()

    return totals


def test_cfcheck_grd(tmpdir: Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    )

    groups = [""]
    while groups:
        group = groups.pop()
        try:
            ds = xr.open_dataset(product_path, engine="sentinel-1", group=group)
            groups.extend(f"{group}/{g}" for g in ds.attrs.get("subgroups", []))
        except FileNotFoundError:
            continue
        nc_path = tmpdir.join(group.replace("/", "-") + ".nc")
        ds.to_netcdf(nc_path)

        totals = cfcheck(str(nc_path))

        assert totals["FATAL"] + totals["ERROR"] + totals["WARN"] == 0
