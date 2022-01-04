import pathlib
import typing as T

from xarray_sentinel import reformat

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_zarr_reformat(tmpdir: T.Any) -> None:
    product_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    )
    tmp_zarr = str(tmpdir.join("tmp.zarr"))

    reformat.to_group_zarr(product_path, tmp_zarr)
