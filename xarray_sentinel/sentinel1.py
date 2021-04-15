import os
import typing as T
import warnings

import numpy as np
import xarray as xr

from xarray_sentinel import conventions, esa_safe
from xarray_sentinel.esa_safe import PathType


def open_gcp_dataset(annotation_path: PathType) -> xr.Dataset:
    geolocation_grid_points = esa_safe.parse_geolocation_grid_points(annotation_path)
    azimuth_time = []
    slant_range_time = []
    line_set = set()
    pixel_set = set()
    for ggp in geolocation_grid_points:
        if ggp["line"] not in line_set:
            azimuth_time.append(np.datetime64(ggp["azimuthTime"]))
            line_set.add(ggp["line"])
        if ggp["pixel"] not in pixel_set:
            slant_range_time.append(ggp["slantRangeTime"])
            pixel_set.add(ggp["pixel"])
    shape = (len(azimuth_time), len(slant_range_time))
    data_vars = {
        "latitude": (
            ("azimuth_time", "slant_range_time"),
            np.full(shape, np.nan),
            {"units": "degrees_north"},
        ),
        "longitude": (
            ("azimuth_time", "slant_range_time"),
            np.full(shape, np.nan),
            {"units": "degrees_east"},
        ),
        "height": (
            ("azimuth_time", "slant_range_time"),
            np.full(shape, np.nan),
            {"units": "m"},
        ),
        "incidenceAngle": (
            ("azimuth_time", "slant_range_time"),
            np.full(shape, np.nan),
            {"units": "degrees"},
        ),
        "elevationAngle": (
            ("azimuth_time", "slant_range_time"),
            np.full(shape, np.nan),
            {"units": "degrees"},
        ),
    }
    line = sorted(line_set)
    pixel = sorted(pixel_set)
    for ggp in geolocation_grid_points:
        for var in data_vars:
            j = line.index(ggp["line"])
            i = pixel.index(ggp["pixel"])
            data_vars[var][1][j, i] = ggp[var]

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        coords={
            "azimuth_time": (
                "azimuth_time",
                [np.datetime64(dt) for dt in sorted(azimuth_time)],
                {"standard_name": "time", "long_name": "azimuth time"},
            ),
            "slant_range_time": (
                "slant_range_time",
                sorted(slant_range_time),
                {"units": "s", "long_name": "slant range time / two-way delay"},
            ),
        },
        attrs={"Conventions": "CF-1.7"},
    )
    return ds


def open_attitude_dataset(annotation_path: PathType) -> xr.Dataset:
    attitude = esa_safe.parse_attitude(annotation_path)
    shape = len(attitude)
    variables = ["q0", "q1", "q2", "wx", "wy", "wz", "pitch", "roll", "yaw"]
    time: T.List[T.Any] = []
    data_vars: T.Dict[str, T.List[T.Any]] = {var: ("time", []) for var in variables}  # type: ignore
    for k in range(shape):
        time.append(attitude[k]["time"])
        for var in variables:
            data_vars[var][1].append(attitude[k][var])

    coords = {
        "time": ("time", time, {"standard_name": "time", "long_name": "time"},),
    }
    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        attrs={"Conventions": "CF-1.7"},
        coords=coords,  # type: ignore
    )

    ds = ds.update({"time": ds.time.astype(np.datetime64)})
    ds = conventions.update_attributes(ds)
    return ds


def open_orbit_dataset(annotation_path: PathType) -> xr.Dataset:
    orbit = esa_safe.parse_orbit(annotation_path)
    shape = len(orbit)

    reference_system = orbit[0]["frame"]
    variables = ["x", "y", "z", "vx", "vy", "vz"]
    data_vars: T.Dict[str, T.List[T.Any]] = {var: ("time", []) for var in variables}  # type: ignore
    time: T.List[T.Any] = []
    for k in range(shape):
        time.append(orbit[k]["time"])
        data_vars["x"][1].append(orbit[k]["position"]["x"])
        data_vars["y"][1].append(orbit[k]["position"]["y"])
        data_vars["z"][1].append(orbit[k]["position"]["z"])
        data_vars["vx"][1].append(orbit[k]["velocity"]["x"])
        data_vars["vy"][1].append(orbit[k]["velocity"]["y"])
        data_vars["vz"][1].append(orbit[k]["velocity"]["z"])
        if orbit[k]["frame"] != reference_system:
            warnings.warn(
                f"reference_system is not consistent in all the state vectors. "
                f"xpath: .//orbit//frame \n File: {str(annotation_path)}"
            )
            reference_system = None

    coords = {
        "time": ("time", time, {"standard_name": "time", "long_name": "time"},),
    }
    attrs = {"Conventions": "CF-1.7"}
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})
    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        attrs=attrs,  # type: ignore
        coords=coords,  # type: ignore
    )
    ds = ds.update({"time": ds.time.astype(np.datetime64)})
    ds = conventions.update_attributes(ds)
    return ds


def find_avalable_groups(product_path: str) -> T.Tuple[T.List[str], T.List[str]]:
    _, manifest = esa_safe.open_manifest(product_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    sub_swaths = product_attrs["xs:instrument_mode_swaths"]
    groups_lev0 = sub_swaths
    groups_lev1 = []
    for sub_swath in sub_swaths:
        for data in METADATA_OPENERS:
            groups_lev1.append(f"{sub_swath}/{data}")
    return groups_lev0, groups_lev1


def open_root_dataset(product_path: str) -> xr.Dataset:
    _, manifest = esa_safe.open_manifest(product_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    sub_swaths = product_attrs["xs:instrument_mode_swaths"]
    product_attrs["groups"] = []
    for sub_swath in sub_swaths:
        for data in METADATA_OPENERS:
            product_attrs["groups"].append(f"{sub_swath}/{data}")
    return xr.Dataset(attrs=product_attrs)  # type: ignore


def open_swath_dataset(product_path: str, group: str) -> xr.Dataset:
    product_attrs = {"groups": ["orbit", "attitude", "gcp"]}
    return xr.Dataset(attrs=product_attrs)  # type: ignore


def get_burst_id(
    product_attrs: T.Dict[str, T.Any], centre: T.Tuple[float, float]
) -> str:
    rounded_centre = np.int_(np.round(centre, 1) * 10)
    n_or_s = "N" if rounded_centre[0] >= 0 else "S"
    e_or_w = "E" if rounded_centre[1] >= 0 else "W"
    return (
        f"R{product_attrs['sat:relative_orbit']:03}"
        f"-{n_or_s}{rounded_centre[0]:03}"
        f"-{e_or_w}{rounded_centre[1]:04}"
    )


def get_burst_info(
    product_path: str, subswath_id: str
) -> T.Dict[str, T.Dict[str, T.Any]]:
    manifest = esa_safe.open_manifest(product_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)

    for filename, filetype in product_files.items():
        if (
            filetype == "s1Level1ProductSchema"
            and f"-{subswath_id.lower()}-" in os.path.basename(filename)
        ):
            annot_path = filename
            break
    annot = os.path.join(os.path.dirname(product_path), annot_path)
    geoloc = esa_safe.parse_geolocation_grid_points(annot)
    swath_timing = esa_safe.parse_swath_timing(annot)
    linesPerBurst = swath_timing["linesPerBurst"]

    burst_geoloc = {}
    for geoloc_item in geoloc:
        burst_id = geoloc_item["line"] // linesPerBurst
        burst_geoloc.setdefault(burst_id, []).append(geoloc_item)

    burst_info = {}
    for burst_pos, burst_geoloc_items in burst_geoloc.items():
        first_and_last = burst_geoloc_items[
            :: len(burst_geoloc_items) - 1
        ]  # TODO: take full lines
        coords = [
            (geoloc_item["longitude"], geoloc_item["latitude"])
            for geoloc_item in first_and_last
        ]
        centre = np.mean(coords, axis=0)
        burst_id = get_burst_id(product_attrs, centre)
        burst_info[burst_id] = dict(centre=centre, burst_pos=burst_pos,)
    return burst_info


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
        group: T.Optional[str] = None,
    ) -> xr.Dataset:

        groups_lev0, groups_lev1 = find_avalable_groups(filename_or_obj)

        if group is None:
            ds = open_root_dataset(filename_or_obj)
        elif group in groups_lev0:
            ds = open_swath_dataset(filename_or_obj, group)
        elif group in groups_lev1:
            subswath, subgroup = group.split("/")
            annotation_path = esa_safe.get_annotation_path(filename_or_obj, subswath)
            ds = METADATA_OPENERS[subgroup](annotation_path)
        else:
            raise ValueError(
                f"Invalid group {group}, please select one of the following groups:"
                f"\n{groups_lev0+groups_lev1}"
            )

        return ds

    def guess_can_open(self, filename_or_obj: T.Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe"}


METADATA_OPENERS = {
    "gcp": open_gcp_dataset,
    "attitude": open_attitude_dataset,
    "orbit": open_orbit_dataset,
}
