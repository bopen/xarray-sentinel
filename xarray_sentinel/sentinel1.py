import os.path
import typing as T
from xml.etree import ElementTree

import numpy as np
import xarray as xr

from xarray_sentinel import esa_safe

SPEED_OF_LIGHT = 299_792_458  # m / s


def open_gcp_dataset(filename: str) -> xr.Dataset:
    annotation = ElementTree.parse(filename)
    geolocation_grid_points = esa_safe.parse_geolocation_grid_points(annotation)
    time = []
    slant_range = []
    line_set = set()
    pixel_set = set()
    for ggp in geolocation_grid_points.values():
        if ggp["line"] not in line_set:
            time.append(np.datetime64(ggp["azimuthTime"]))
            line_set.add(ggp["line"])
        if ggp["pixel"] not in pixel_set:
            slant_range.append(ggp["slantRangeTime"] * SPEED_OF_LIGHT / 2)
            pixel_set.add(ggp["pixel"])
    shape = (len(time), len(slant_range))
    data_vars = {
        "latitude": (("time", "range"), np.zeros(shape)),
        "longitude": (("time", "range"), np.zeros(shape)),
        "height": (("time", "range"), np.zeros(shape)),
        "incidenceAngle": (("time", "range"), np.zeros(shape)),
        "elevationAngle": (("time", "range"), np.zeros(shape)),
    }
    line = sorted(line_set)
    pixel = sorted(pixel_set)
    for ggp in geolocation_grid_points.values():
        for var in data_vars:
            j = line.index(ggp["line"])
            i = pixel.index(ggp["pixel"])
            data_vars[var][1][j, i] = ggp[var]

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        coords={
            "time": (
                "time",
                [np.datetime64(dt) for dt in sorted(time)],
                {"standard_name": "time", "long_name": "azimuth time"},
            ),
            "range": (
                "range",
                sorted(slant_range),
                {"units": "m", "long_name": "slant range / line-of-sight distance"},
            ),
        },
    )
    return ds


def open_root_dataset(filename: str) -> xr.Dataset:
    manifest = esa_safe.open_manifest(filename)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    product_attrs["groups"] = ["orbit"] + product_attrs["xs:instrument_mode_swaths"]
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
        elif group == "gcp":
            ds = open_gcp_dataset(filename_or_obj)
        return ds

    def guess_can_open(self, filename_or_obj: T.Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe"}
