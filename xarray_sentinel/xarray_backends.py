import os
import warnings
from typing import Any

import fsspec
import xarray as xr

from . import eopf_product, sentinel1


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    supports_groups = True

    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: tuple[str] | None = None,
        group: str | None = None,
        storage_options: dict[str, Any] | None = None,
        override_product_files: str | None = None,
        fs: fsspec.AbstractFileSystem | None = None,
        check_files_exist: bool = False,
        parse_geospatial_attrs: bool = True,
        rasterio_chunks: dict[str, int] | None = None,
    ) -> xr.Dataset:
        ds = sentinel1.open_sentinel1_dataset(
            filename_or_obj,
            drop_variables=drop_variables,
            group=group,
            storage_options=storage_options,
            override_product_files=override_product_files,
            fs=fs,
            check_files_exist=check_files_exist,
            parse_geospatial_attrs=parse_geospatial_attrs,
            rasterio_chunks=rasterio_chunks,
        )
        return ds

    def open_datatree(  # type: ignore
        self,
        filename_or_obj: str,
        *,
        drop_variables: tuple[str] | None = None,
        storage_options: dict[str, Any] | None = None,
        override_product_files: str | None = None,
        fs: fsspec.AbstractFileSystem | None = None,
        check_files_exist: bool = False,
        rasterio_chunks: dict[str, int] | None = None,
        **kwargs: Any,
    ) -> xr.DataTree:
        """Open a SAFE product as an experimental EOPF-layout DataTree."""
        if drop_variables is not None:
            warnings.warn("'drop_variables' is currently ignored")
        datatree = eopf_product.open_datatree(
            filename_or_obj,
            storage_options=storage_options,
            override_product_files=override_product_files,
            fs=fs,
            check_files_exist=check_files_exist,
            rasterio_chunks=rasterio_chunks,
        )
        return datatree

    def open_groups_as_dict(  # type: ignore
        self,
        filename_or_obj: str,
        *,
        drop_variables: tuple[str] | None = None,
        storage_options: dict[str, Any] | None = None,
        override_product_files: str | None = None,
        fs: fsspec.AbstractFileSystem | None = None,
        check_files_exist: bool = False,
        rasterio_chunks: dict[str, int] | None = None,
        **kwargs: Any,
    ) -> dict[str, xr.Dataset]:
        """Open the experimental EOPF-layout groups as a dictionary."""
        datatree = self.open_datatree(
            filename_or_obj,
            drop_variables=drop_variables,
            storage_options=storage_options,
            override_product_files=override_product_files,
            fs=fs,
            check_files_exist=check_files_exist,
            rasterio_chunks=rasterio_chunks,
        )
        groups = {}
        for node in datatree.subtree:
            groups[node.path] = node.to_dataset(inherit=False)
        return groups

    def guess_can_open(self, filename_or_obj: Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe", ".safe/"}
