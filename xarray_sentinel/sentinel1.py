import os
import typing as T
import warnings

import numpy as np
import pandas as pd  # type: ignore
import rioxarray  # type: ignore
import xarray as xr

from xarray_sentinel import conventions, esa_safe


def open_gcp_dataset(annotation_path: esa_safe.PathType) -> xr.Dataset:
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
    dims = ("azimuth_time", "slant_range_time")
    data_vars = {
        "latitude": (dims, np.full(shape, np.nan)),
        "longitude": (dims, np.full(shape, np.nan)),
        "height": (dims, np.full(shape, np.nan)),
        "incidenceAngle": (dims, np.full(shape, np.nan)),
        "elevationAngle": (dims, np.full(shape, np.nan)),
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
            "azimuth_time": [np.datetime64(dt) for dt in sorted(azimuth_time)],
            "slant_range_time": sorted(slant_range_time),
        },
    )
    conventions.update_attributes(ds, group="gcp")
    return ds


def open_attitude_dataset(annotation_path: esa_safe.PathType) -> xr.Dataset:
    attitude = esa_safe.parse_attitude(annotation_path)
    shape = len(attitude)
    variables = ["q0", "q1", "q2", "q3", "wx", "wy", "wz", "pitch", "roll", "yaw"]
    time: T.List[T.Any] = []
    data_vars: T.Dict[str, T.List[T.Any]] = {var: ("time", []) for var in variables}  # type: ignore
    for k in range(shape):
        time.append(attitude[k]["time"])
        for var in variables:
            data_vars[var][1].append(attitude[k][var])

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        coords={"time": [np.datetime64(dt) for dt in time]},
    )
    ds = ds.rename({"time": "azimuth_time"})
    ds = conventions.update_attributes(ds, group="attitude")
    return ds


def open_orbit_dataset(annotation_path: esa_safe.PathType) -> xr.Dataset:
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
                f"xpath: .//orbit//frame \nFile: {str(annotation_path)}"
            )
            reference_system = None

    attrs = {}
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        attrs=attrs,  # type: ignore
        coords={"time": [np.datetime64(dt) for dt in time]},
    )
    ds = ds.rename({"time": "azimuth_time"})
    ds = conventions.update_attributes(ds, group="orbit")
    return ds


def find_avalable_groups(
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]],
    product_attrs: T.Dict[str, T.Any],
) -> T.Dict[str, T.Dict[str, T.Any]]:

    ancillary_data_paths = filter_missing_path(ancillary_data_paths)
    groups: T.Dict[str, T.Dict[str, T.Any]] = {}
    for subswath_id, subswath_data_path in ancillary_data_paths.items():
        subswath_id = subswath_id.upper()
        if len(subswath_data_path["annotation_path"]) == 0:
            continue
        annotation_path = list(subswath_data_path["annotation_path"].values())[0]
        gcp = open_gcp_dataset(annotation_path)
        centres_lat, centres_lon = compute_burst_centres(gcp)
        burst_ids: T.List[str] = []
        for k in range(len(centres_lat)):
            burst_ids.append(
                build_burst_id(
                    centres_lat[k], centres_lon[k], product_attrs["sat:relative_orbit"]
                )
            )

        subgroups = list(METADATA_OPENERS.keys()) + burst_ids

        groups[subswath_id] = {"subgroups": subgroups, **subswath_data_path}
        for subgroup in METADATA_OPENERS.keys():
            groups[f"{subswath_id}/{subgroup}"] = subswath_data_path
        for k, burst_id in enumerate(burst_ids):
            groups[f"{subswath_id}/{burst_id}"] = {
                "burst_position": k,
                **subswath_data_path,
            }
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
    manifest_path: esa_safe.PathType,
    groups: T.Dict[str, T.Dict[str, T.Collection[str]]],
) -> xr.Dataset:
    manifest_path, manifest = esa_safe.open_manifest(manifest_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    attrs = dict(product_attrs, groups=list(groups.keys()))
    ds = xr.Dataset(attrs=attrs)  # type: ignore
    conventions.update_attributes(ds)
    return ds


def open_swath_dataset(
    manifest_path: esa_safe.PathType, subgrups: T.List[int],
) -> xr.Dataset:
    manifest_path, manifest = esa_safe.open_manifest(manifest_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    attrs = dict(product_attrs, groups=subgrups)
    ds = xr.Dataset(attrs=attrs)  # type: ignore
    conventions.update_attributes(ds)
    return ds


def open_burst_dataset(
    manifest_path: esa_safe.PathType,
    burst_position: int,
    measurement_paths: T.Dict[str, esa_safe.PathType],
    annotation_path: esa_safe.PathType,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    manifest_path, manifest = esa_safe.open_manifest(manifest_path)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    image_information = esa_safe.parse_image_information(annotation_path)
    procduct_information = esa_safe.parse_product_information(annotation_path)

    swath_timing = esa_safe.parse_swath_timing(annotation_path)
    linesPerBurst = swath_timing["linesPerBurst"]
    samplesPerBurst = swath_timing["samplesPerBurst"]

    first_azimuth_time = pd.to_datetime(
        swath_timing["burstList"]["burst"][burst_position]["azimuthTime"]
    )
    azimuth_time_interval = pd.to_timedelta(
        image_information["azimuthTimeInterval"], "s"
    )
    azimuth_time = pd.date_range(
        start=first_azimuth_time, periods=linesPerBurst, freq=azimuth_time_interval,
    )

    slantRangeTime = image_information["slantRangeTime"]
    slant_range_sampling = 1 / procduct_information["rangeSamplingRate"]

    slant_range_time = np.linspace(
        slantRangeTime,
        slantRangeTime + slant_range_sampling * (samplesPerBurst - 1),
        samplesPerBurst,
    )
    burst_first_line = burst_position * linesPerBurst
    burst_last_line = (burst_position + 1) * linesPerBurst - 1
    burst_first_pixel = 0
    burst_last_pixel = samplesPerBurst - 1

    data_vars = {}
    for pol, data_path in measurement_paths.items():
        arr = rioxarray.open_rasterio(data_path, chunks=chunks)

        arr = arr.squeeze("band").drop_vars(["band", "spatial_ref"])
        arr = arr.isel(
            x=slice(burst_first_pixel, burst_last_pixel + 1),
            y=slice(burst_first_line, burst_last_line + 1),
        )
        data_vars[pol.upper()] = arr

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        coords={
            "azimuth_time": ("y", azimuth_time),
            "slant_range_time": ("x", slant_range_time),
        },
        attrs=product_attrs,  # type: ignore
    )
    ds = ds.swap_dims({"y": "azimuth_time", "x": "slant_range_time"})
    ds = ds.drop_vars({"y", "x"})
    conventions.update_attributes(ds)
    return ds


def build_burst_id(lat: float, lon: float, relative_orbit: int,) -> str:
    lat = int(round(lat * 10))
    lon = int(round(lon * 10))

    n_or_s = "N" if lat >= 0 else "S"
    e_or_w = "E" if lon >= 0 else "W"
    burst_id = f"R{relative_orbit:03}" f"-{n_or_s}{lat:03}" f"-{e_or_w}{lon:04}"
    return burst_id


def compute_burst_centres(gcp: xr.Dataset) -> T.Tuple[np.ndarray, np.ndarray]:
    gcp_rolling = gcp.rolling(azimuth_time=2, min_periods=1)
    gc_az_win = gcp_rolling.construct(azimuth_time="az_win")
    centre = gc_az_win.mean(["az_win", "slant_range_time"])
    centre = centre.isel(azimuth_time=slice(1, None))
    return centre.latitude.values, centre.longitude.values


def open_dataset(
    filename_or_obj: esa_safe.PathType,
    drop_variables: T.Optional[T.Tuple[str]] = None,
    group: T.Optional[str] = None,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    manifest_path, manifest = esa_safe.open_manifest(filename_or_obj)
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    ancillary_data_paths = esa_safe.get_ancillary_data_paths(
        manifest_path, product_files
    )

    groups = find_avalable_groups(ancillary_data_paths, product_attrs)

    if group is None:
        ds = open_root_dataset(manifest_path, groups)
    elif group not in groups:
        raise ValueError(
            f"Invalid group {group}, please select one of the following groups:"
            f"\n{list(groups.keys())}"
        )
    elif "/" not in group:
        ds = open_swath_dataset(manifest_path, groups[group]["subgroups"])
    else:
        subswath, subgroup = group.split("/", 1)
        if subgroup in METADATA_OPENERS:
            annotation_path = list(groups[group]["annotation_path"].values())[0]
            ds = METADATA_OPENERS[subgroup](annotation_path)
        else:
            annotation_path = list(groups[group]["annotation_path"].values())[0]
            ds = open_burst_dataset(
                manifest_path,
                measurement_paths=groups[group]["measurement_path"],
                burst_position=groups[group]["burst_position"],
                annotation_path=annotation_path,
                chunks=chunks,
            )
    return ds


class Sentinel1Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        drop_variables: T.Optional[T.Tuple[str]] = None,
        group: T.Optional[str] = None,
    ) -> xr.Dataset:

        return open_dataset(filename_or_obj, drop_variables, group)

    def guess_can_open(self, filename_or_obj: T.Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe", ".safe/"}


METADATA_OPENERS = {
    "gcp": open_gcp_dataset,
    "attitude": open_attitude_dataset,
    "orbit": open_orbit_dataset,
}
