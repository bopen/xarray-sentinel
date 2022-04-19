import pathlib
import typing as T

import pytest
import xarray as xr
from cfchecker import cfchecks

pytest.importorskip("netCDF4")

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def cfcheck(path: str):
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

    totals = inst.get_total_counts()

    return totals


def test_cfcheck(tmpdir: T.Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_GRDH_1SDV_20211223T051122_20211223T051147_030148_039993_5371.SAFE"
    )

    groups = [""]
    while groups:
        group = groups.pop()
        print(group)
        try:
            ds = xr.open_dataset(product_path, engine="sentinel-1", group=group)
            groups.extend(f"{group}/{g}" for g in ds.attrs.get("subgroups", []))
        except:
            pass
        nc_path = tmpdir.join(group.replace("/", "-") + ".nc")
        ds.to_netcdf(nc_path)

        totals = cfcheck(str(nc_path))

        assert totals["FATAL"] + totals["ERROR"] + totals["WARN"] == 0
