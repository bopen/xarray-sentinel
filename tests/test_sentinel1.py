import pathlib
import tempfile

import numpy as np

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


def test_get_burst_info() -> None:
    base_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    subswath_data = {
        "annotation_path": {
            "vh": str(
                base_path
                / "annotation/s1b-iw1-slc-vh-20210401t052624-20210401t052649-026269-032297-001.xml"
            ),
        },
    }
    product_attrs = {"sat:relative_orbit": 168}
    partial_expected_burst_info = {
        "R168-N118-E0472": {
            "burst_centre": np.array([11.8475875, 47.16626783]),
            "burst_pos": 0,
            "burst_first_line": 0,
            "burst_last_line": 1500,
            "burst_first_pixel": 0,
            "burst_last_pixel": 21631,
        },
    }

    burst_info = sentinel1.get_burst_info(product_attrs, subswath_data)
    assert burst_info is not None

    for burst_id in partial_expected_burst_info:
        assert np.allclose(
            np.asanyarray(burst_info[burst_id]["burst_centre"]),
            np.asanyarray(partial_expected_burst_info[burst_id]["burst_centre"]),
        )
        del burst_info[burst_id]["burst_centre"]
        del partial_expected_burst_info[burst_id]["burst_centre"]
        assert burst_info[burst_id] == partial_expected_burst_info[burst_id]


def test_find_avalable_groups() -> None:
    base_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    ancillary_data_paths = {
        "iw1": {
            "annotation_path": {
                "vv": f"{base_path}/annotation/"
                + "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml",
            },
        },
    }
    product_attrs = {"sat:relative_orbit": 168}
    expected_groups = {
        "IW1",
        "IW1/attitude",
        "IW1/gcp",
        "IW1/orbit",
        "IW1/R168-N115-E0457",
        "IW1/R168-N116-E0460",
        "IW1/R168-N116-E0462",
        "IW1/R168-N116-E0463",
        "IW1/R168-N117-E0465",
        "IW1/R168-N117-E0467",
        "IW1/R168-N118-E0468",
        "IW1/R168-N118-E0470",
        "IW1/R168-N118-E0472",
    }

    groups = sentinel1.find_avalable_groups(ancillary_data_paths, product_attrs)
    assert set(groups) == expected_groups
