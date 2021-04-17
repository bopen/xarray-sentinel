import os
import typing as T
import warnings

import numpy as np
import rioxarray  # type: ignore
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


def find_avalable_groups(
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]],
    product_attrs: T.Dict[str, T.Any],
) -> T.Dict[str, T.Dict[str, T.Any]]:

    ancillary_data_paths = filter_missing_path(ancillary_data_paths)
    groups: T.Dict[str, T.Dict[str, T.Any]] = {}
    for subswath_id, subswath_data_path in ancillary_data_paths.items():
        subswath_id = subswath_id.upper()
        burst_info = get_burst_info(product_attrs, subswath_data_path)
        if burst_info is None:
            continue
        subgroups = list(METADATA_OPENERS.keys()) + list(burst_info.keys())
        groups[subswath_id] = dict(subswath_data_path, subgroups=subgroups)
        for subgroup in METADATA_OPENERS.keys():
            groups[f"{subswath_id}/{subgroup}"] = subswath_data_path
        for burst_id, burst_data in burst_info.items():
            full_data = dict(subswath_data_path, **burst_data)
            groups[f"{subswath_id}/{burst_id}"] = full_data
    return groups


def filter_missing_path(path_dict: T.Dict[str, T.Any]) -> T.Dict[str, T.Any]:

    path_dict_copy = path_dict.copy()
    for k in path_dict:
        if isinstance(path_dict[k], dict):
            path_dict_copy[k] = filter_missing_path(path_dict[k])
        else:
            if not os.path.exists(path_dict[k]):
                del path_dict_copy[k]
    return path_dict_copy


def open_root_dataset(
    product_attrs: T.Dict[str, str], groups: T.Dict[str, T.Dict[str, T.Collection[str]]]
) -> xr.Dataset:
    attrs = dict(product_attrs, groups=list(groups.keys()))
    return xr.Dataset(attrs=attrs)  # type: ignore


def open_swath_dataset(
    product_attrs: T.Dict[str, str],
    swath_id: str,
    swath_data: T.Dict[str, T.Collection[str]],
) -> xr.Dataset:
    attrs = dict(product_attrs, groups=swath_data["subgroups"])
    return xr.Dataset(attrs=attrs)  # type: ignore


def open_burst_dataset(
    product_attrs: T.Dict[str, str], burst_id: str, burst_data: T.Dict[str, T.Any]
) -> xr.Dataset:
    ds_pol = {
        pol.upper(): rioxarray.open_rasterio(datafile)
        for pol, datafile in burst_data["measurement"].items()
    }
    ds = xr.merge([ds_pol])
    ds.attrs.update(product_attrs)  # type: ignore
    ds = ds.squeeze("band").drop(["band", "spatial_ref"])
    ds = ds.isel(
        x=slice(burst_data["burst_first_pixel"], burst_data["burst_last_pixel"] + 1),
        y=slice(burst_data["burst_first_line"], burst_data["burst_last_line"] + 1),
    )
    return ds


def build_burst_id(
    product_attrs: T.Dict[str, T.Any], burst_centre: np.typing.ArrayLike,
) -> str:
    rounded_centre = np.int_(np.round(burst_centre, 1) * 10)
    n_or_s = "N" if rounded_centre[0] >= 0 else "S"
    e_or_w = "E" if rounded_centre[1] >= 0 else "W"
    burst_id = (
        f"R{product_attrs['sat:relative_orbit']:03}"
        f"-{n_or_s}{rounded_centre[0]:03}"
        f"-{e_or_w}{rounded_centre[1]:04}"
    )
    return burst_id


def compute_burst_center(burst_gcp: T.List[T.Dict[str, float]]) -> np.ndarray:
    first_and_last = burst_gcp[:: len(burst_gcp) - 1]  # TODO: take full lines
    coords = [
        (geoloc_item["longitude"], geoloc_item["latitude"])
        for geoloc_item in first_and_last
    ]
    centre = np.mean(coords, axis=0)
    return centre  # type: ignore


def get_bursts_gcp(
    subswath_gcp: T.List[T.Dict[str, T.Any]], linesPerBurst: int
) -> T.Dict[int, T.List[T.Dict[str, T.Any]]]:

    burst_gcp: T.Dict[int, T.List[T.Dict[str, T.Any]]] = {}
    for gcp in subswath_gcp:
        burst_id = gcp["line"] // linesPerBurst
        burst_gcp.setdefault(burst_id, []).append(gcp)
    return burst_gcp


def get_burst_info(
    product_attrs: T.Dict[str, T.Any], subswath_data: T.Dict[str, T.Dict[str, str]],
) -> T.Optional[T.Dict[str, T.Dict[str, T.Any]]]:
    if len(subswath_data["annotation_path"]) == 0:
        return None
    annotation_path = list(subswath_data["annotation_path"].values())[0]
    subswath_gcp = esa_safe.parse_geolocation_grid_points(annotation_path)

    swath_timing = esa_safe.parse_swath_timing(annotation_path)
    linesPerBurst = int(swath_timing["linesPerBurst"])
    samplesPerBurst = int(swath_timing["samplesPerBurst"])

    bursts_gcp = get_bursts_gcp(subswath_gcp, linesPerBurst)

    burst_info = {}
    for burst_pos, burst_gcp in bursts_gcp.items():
        centre = compute_burst_center(burst_gcp)
        burst_id = build_burst_id(product_attrs, centre)
        burst_info[burst_id] = dict(
            burst_centre=centre,
            burst_pos=burst_pos,
            burst_first_line=burst_pos * linesPerBurst,
            burst_last_line=(burst_pos + 1) * linesPerBurst - 1,
            burst_first_pixel=0,
            burst_last_pixel=samplesPerBurst - 1,
        )
    return burst_info


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
        group: T.Optional[str] = None,
    ) -> xr.Dataset:

        manifest_path, manifest = esa_safe.open_manifest(filename_or_obj)
        product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
        ancillary_data_paths = esa_safe.get_ancillary_data_paths(
            manifest_path, product_files
        )

        groups = find_avalable_groups(ancillary_data_paths, product_attrs)

        if group is None:
            ds = open_root_dataset(product_attrs, groups)
        elif group not in groups:
            raise ValueError(
                f"Invalid group {group}, please select one of the following groups:"
                f"\n{list(groups.keys())}"
            )
        elif "/" not in group:
            ds = open_swath_dataset(product_attrs, group, groups[group])
        else:
            subswath, subgroup = group.split("/", 1)
            if subgroup in METADATA_OPENERS:
                annotation_path = list(groups[group]["annotation_path"].values())[0]
                ds = METADATA_OPENERS[subgroup](annotation_path)
            else:
                ds = open_burst_dataset(product_attrs, group, groups[group])

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
