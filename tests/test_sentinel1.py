import pathlib
import tempfile

from xarray_sentinel import sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_filter_missing_path() -> None:
    existing_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )

    missing_path = tempfile.mktemp()
    ancillary_data_paths = {
        "paths1": {"path1": existing_path, "path2": missing_path},
        "paths2": {"path1": missing_path, "path2": missing_path},
    }

    res = sentinel1.filter_missing_path(ancillary_data_paths)
    expected = {"paths1": {"path1": existing_path}, "paths2": {}}

    assert res == expected


def test_build_burst_id() -> None:
    product_attrs = {"sat:relative_orbit": 168}
    burst_centre = [11.8475875, 47.16626783]
    burst_id = sentinel1.build_burst_id(product_attrs, burst_centre)
    assert burst_id == "R168-N118-E0472"
