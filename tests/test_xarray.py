import pathlib

import xarray as xr

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_open_dataset_root() -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert res.attrs["constellation"] == "sentinel-1"
    assert res.attrs["sar:product_type"] == "SLC"
    assert res.attrs["sar:instrument_mode"] == "IW"

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)

    product_path = product_path / "manifest.safe"

    res = xr.open_dataset(product_path, engine="sentinel-1")  # type: ignore

    assert isinstance(res, xr.Dataset)

    res = xr.open_dataset(product_path)  # type: ignore

    assert isinstance(res, xr.Dataset)


def test_open_dataset_gcp() -> None:
    annotation_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
        / "annotation"
        / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
    )
    res = xr.open_dataset(annotation_path, engine="sentinel-1", group="gcp")  # type: ignore

    assert isinstance(res, xr.Dataset)
    assert set(res.dims) == {"time", "slant_range"}
