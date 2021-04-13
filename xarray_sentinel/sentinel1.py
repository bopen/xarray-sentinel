import os.path
import typing as T

import xarray as xr

from xarray_sentinel import esa_safe
from xarray_sentinel.datasets import OPENERS


def read_subswaths(
        product_path: str,
) -> T.List:
    manifest = esa_safe.open_manifest(product_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    return product_files


def get_groups(subswaths):
    groups = []
    for sub_swath in subswaths:
        for dataset in OPENERS:
            groups.append(sub_swath + "/" + dataset)
    return groups


def open_root_dataset(
        product_path: str,
) -> xr.Dataset:
    manifest = esa_safe.open_manifest(product_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    sub_swaths = product_attrs["xs:instrument_mode_swaths"]
    product_attrs["groups"] = []
    for sub_swath in sub_swaths:
        for data in OPENERS:
            product_attrs["groups"].append(sub_swath + "/" + data)
    return xr.Dataset(attrs=product_attrs)  # type: ignore


def open_annotation(product_path: str) -> xr.Dataset:
    product_attrs = {"groups": ["orbit", "attitude", "gcp"]}
    return xr.Dataset(attrs=product_attrs)  # type: ignore


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
        group: T.Optional[str] = None,
    ) -> xr.Dataset:
        if group is None:
            ds = open_root_dataset(filename_or_obj)
            return ds
        else:
            subswath, subgroup = group.split('/')
            annotation_path = esa_safe.get_annotation_path(filename_or_obj, subswath)
            ds = OPENERS[subgroup](annotation_path)
        return ds

    def guess_can_open(self, filename_or_obj: T.Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe"}
