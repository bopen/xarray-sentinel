import os
import typing as T
import warnings

import fsspec  # type: ignore
import numpy as np
import numpy.typing as NT
import pandas as pd  # type: ignore
import rioxarray  # type: ignore
import xarray as xr

from xarray_sentinel import conventions, esa_safe


def open_calibration_dataset(calibration_path: esa_safe.PathType) -> xr.Dataset:
    calibration_vectors = esa_safe.parse_calibration_vectors(calibration_path)
    azimuth_time_list = []
    pixel_list = []
    line_list = []
    sigmaNought_list = []
    betaNought_list = []
    gamma_list = []
    dn_list = []

    for vector in calibration_vectors:
        azimuth_time_list.append(vector["azimuthTime"])
        line_list.append(vector["line"])
        pixel = np.fromstring(vector["pixel"]["$"], dtype=int, sep=" ")  # type: ignore
        pixel_list.append(pixel)
        sigmaNought = np.fromstring(vector["sigmaNought"]["$"], dtype=float, sep=" ")  # type: ignore
        sigmaNought_list.append(sigmaNought)
        betaNought = np.fromstring(vector["betaNought"]["$"], dtype=float, sep=" ")  # type: ignore
        betaNought_list.append(betaNought)
        gamma = np.fromstring(vector["gamma"]["$"], dtype=float, sep=" ")  # type: ignore
        gamma_list.append(gamma)
        dn = np.fromstring(vector["dn"]["$"], dtype=float, sep=" ")  # type: ignore
        dn_list.append(dn)

    pixel = np.array(pixel_list)
    if not np.allclose(pixel, pixel[0]):
        raise ValueError(
            "Unable to organise calibration vectors in a regular line-pixel grid"
        )
    data_vars = dict(
        azimuth_time=xr.DataArray(azimuth_time_list, dims="line"),
        sigmaNought=xr.DataArray(sigmaNought_list, dims=("line", "pixel")),
        betaNought=xr.DataArray(betaNought_list, dims=("line", "pixel")),
        gamma=xr.DataArray(gamma_list, dims=("line", "pixel")),
        dn=xr.DataArray(dn_list, dims=("line", "pixel")),
    )
    coords = dict(
        line=xr.DataArray(line_list, dims="line"),
        pixel=xr.DataArray(pixel_list[0], dims="pixel"),
    )

    return xr.Dataset(data_vars=data_vars, coords=coords)


def open_coordinateConversion_dataset(annotation_path: esa_safe.PathType) -> xr.Dataset:

    coordinateConversionList = esa_safe.parse_tag_dict(
        annotation_path, "product", ".//coordinateConversionList"
    )
    gr0 = []
    sr0 = []
    azimuthTime = []
    slantRangeTime = []
    srgrCoefficients = []
    grsrCoefficients = []
    for values in coordinateConversionList["coordinateConversion"]:
        sr0.append(values["sr0"])
        gr0.append(values["gr0"])
        azimuthTime.append(values["azimuthTime"])
        slantRangeTime.append(values["slantRangeTime"])
        srgrCoefficients.append(
            np.fromstring(values["srgrCoefficients"]["$"], dtype=float, sep=" ")  # type: ignore
        )
        grsrCoefficients.append(
            np.fromstring(values["grsrCoefficients"]["$"], dtype=float, sep=" ")  # type: ignore
        )

    coords = {
        "azimuth_time": xr.DataArray(azimuthTime, dims="azimuth_time"),
        "exponent": xr.DataArray(np.arange(len(srgrCoefficients[0])), dims="exponent"),
    }

    data_vars = {
        "gr0": xr.DataArray(gr0, dims="azimuth_time"),
        "sr0": xr.DataArray(sr0, dims="azimuth_time"),
        "slant_range_time": xr.DataArray(slantRangeTime, dims=("azimuth_time")),
        "srgr_coefficients": xr.DataArray(
            srgrCoefficients, dims=("azimuth_time", "exponent")
        ),
        "grsr_coefficients": xr.DataArray(
            grsrCoefficients, dims=("azimuth_time", "exponent")
        ),
    }
    return xr.Dataset(data_vars=data_vars, coords=coords)


def get_fs_path(
    urlpath_or_path: esa_safe.PathType, fs: T.Optional[fsspec.AbstractFileSystem] = None
) -> T.Tuple[fsspec.AbstractFileSystem, str]:
    if fs is None:
        fs, _, paths = fsspec.get_fs_token_paths(urlpath_or_path)
        if len(paths) == 0:
            raise ValueError(f"file or object not found {urlpath_or_path!r}")
        elif len(paths) > 1:
            raise ValueError(f"multiple files or objects found {urlpath_or_path!r}")
        path = paths[0]
    else:
        path = urlpath_or_path
    return fs, path


def open_gcp_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    geolocation_grid_points = esa_safe.parse_geolocation_grid_points(annotation)
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
        data_vars=data_vars,
        coords={
            "azimuth_time": [np.datetime64(dt) for dt in azimuth_time],
            "slant_range_time": slant_range_time,
            "line": ("azimuth_time", line),
            "pixel": ("slant_range_time", pixel),
        },
    )
    conventions.update_attributes(ds, group="gcp")
    return ds


def open_attitude_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    attitude = esa_safe.parse_attitude(annotation)
    shape = len(attitude)
    variables = ["q0", "q1", "q2", "q3", "wx", "wy", "wz", "pitch", "roll", "yaw"]
    time: T.List[T.Any] = []
    data_vars: T.Dict[str, T.Any] = {var: ("time", []) for var in variables}
    for k in range(shape):
        time.append(attitude[k]["time"])
        for var in variables:
            data_vars[var][1].append(attitude[k][var])

    ds = xr.Dataset(
        data_vars=data_vars, coords={"time": [np.datetime64(dt) for dt in time]},
    )
    ds = ds.rename({"time": "azimuth_time"})
    ds = conventions.update_attributes(ds, group="attitude")
    return ds


def open_orbit_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    orbit = esa_safe.parse_orbit(annotation)
    shape = len(orbit)

    reference_system = orbit[0]["frame"]
    variables = ["position", "velocity"]
    data: T.Dict[str, T.List[T.Any]] = {var: [[], [], []] for var in variables}
    time: T.List[T.Any] = []
    for k in range(shape):
        time.append(orbit[k]["time"])
        data["position"][0].append(orbit[k]["position"]["x"])
        data["position"][1].append(orbit[k]["position"]["y"])
        data["position"][2].append(orbit[k]["position"]["z"])
        data["velocity"][0].append(orbit[k]["velocity"]["x"])
        data["velocity"][1].append(orbit[k]["velocity"]["y"])
        data["velocity"][2].append(orbit[k]["velocity"]["z"])
        if orbit[k]["frame"] != reference_system:
            warnings.warn(
                "reference_system is not consistent in all the state vectors. "
            )
            reference_system = None

    position = xr.Variable(data=data["position"], dims=("axis", "time"))  # type: ignore
    velocity = xr.Variable(data=data["velocity"], dims=("axis", "time"))  # type: ignore

    attrs = {}
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})

    ds = xr.Dataset(
        data_vars={"position": position, "velocity": velocity},
        attrs=attrs,
        coords={"time": [np.datetime64(dt) for dt in time], "axis": ["x", "y", "z"]},
    )
    ds = ds.rename({"time": "azimuth_time"})
    ds = conventions.update_attributes(ds, group="orbit")
    return ds


def find_avalable_groups(
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]],
    product_attrs: T.Dict[str, T.Any],
    fs: fsspec.AbstractFileSystem = fsspec.filesystem("file"),
) -> T.Dict[str, T.Dict[str, T.Any]]:

    ancillary_data_paths = filter_missing_path(ancillary_data_paths, fs)
    groups: T.Dict[str, T.Dict[str, T.Any]] = {}
    for subswath_id, subswath_data_path in ancillary_data_paths.items():
        subswath_id = subswath_id.upper()
        if len(subswath_data_path["annotation_path"]) == 0:
            continue
        annotation_path = list(subswath_data_path["annotation_path"].values())[0]

        with fs.open(annotation_path) as annotation_file:
            swath_timing = esa_safe.parse_swath_timing(annotation_file)

        number_of_bursts = swath_timing["burstList"]["@count"]

        burst_ids: T.List[str] = []
        if number_of_bursts > 0:
            with fs.open(annotation_path) as annotation_file:
                gcp = open_gcp_dataset(annotation_file)
            centres_lat, centres_lon = compute_burst_centres(gcp)

            for k in range(len(centres_lat)):
                burst_ids.append(
                    build_burst_id(
                        centres_lat[k],
                        centres_lon[k],
                        product_attrs["sat:relative_orbit"],
                    )
                )

        subgroups = list(METADATA_OPENERS.keys()) + ["calibration"] + burst_ids

        groups[subswath_id] = {"subgroups": subgroups, **subswath_data_path}
        groups[f"{subswath_id}/calibration"] = subswath_data_path
        for subgroup in METADATA_OPENERS.keys():
            groups[f"{subswath_id}/{subgroup}"] = subswath_data_path
        for k, burst_id in enumerate(burst_ids):
            groups[f"{subswath_id}/{burst_id}"] = {
                "burst_position": k,
                **subswath_data_path,
            }
    return groups


def filter_missing_path(
    path_dict: T.Dict[str, T.Any],
    fs: fsspec.AbstractFileSystem = fsspec.filesystem("file"),
) -> T.Dict[str, T.Any]:

    path_dict_copy = path_dict.copy()
    for k in path_dict:
        if isinstance(path_dict[k], dict):
            path_dict_copy[k] = filter_missing_path(path_dict[k], fs)
        else:
            if not fs.exists(path_dict[k]):
                del path_dict_copy[k]
    return path_dict_copy


def open_root_dataset(
    product_attrs: T.Dict[str, T.Any],
    groups: T.Dict[str, T.Dict[str, T.Collection[str]]],
) -> xr.Dataset:
    attrs = dict(product_attrs, groups=list(groups.keys()))
    ds = xr.Dataset(attrs=attrs)
    conventions.update_attributes(ds)
    return ds


def open_swath_dataset(
    manifest_path: esa_safe.PathType,
    measurement_paths: T.Dict[str, esa_safe.PathType],
    subgrups: T.List[int],
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest_path)
    attrs = dict(product_attrs, groups=subgrups)

    data_vars = {}
    for pol, data_path in measurement_paths.items():
        arr = rioxarray.open_rasterio(data_path, chunks=chunks)
        arr = arr.squeeze("band").drop_vars(["band", "spatial_ref"])
        arr = arr.assign_coords(
            {
                "x": np.arange(0, arr["x"].size, dtype=int),
                "y": np.arange(0, arr["y"].size, dtype=int),
            }
        )
        arr = arr.rename({"y": "line", "x": "pixel"})
        data_vars[pol.upper()] = arr

    ds = xr.Dataset(data_vars=data_vars, attrs=attrs,)
    conventions.update_attributes(ds)
    return ds


def open_burst_dataset(
    manifest_path: esa_safe.PathType,
    burst_position: int,
    measurement_paths: T.Dict[str, esa_safe.PathType],
    annotation_path: esa_safe.PathType,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    product_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest_path)
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
        arr = arr.assign_coords(
            {
                "x": np.arange(burst_first_pixel, burst_last_pixel + 1, dtype=int),
                "y": np.arange(burst_first_line, burst_last_line + 1, dtype=int),
            }
        )
        arr = arr.rename({"y": "line", "x": "pixel"})
        data_vars[pol.upper()] = arr

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "azimuth_time": ("line", azimuth_time),
            "slant_range_time": ("pixel", slant_range_time),
        },
        attrs=product_attrs,
    )
    ds = ds.swap_dims({"line": "azimuth_time", "pixel": "slant_range_time"})
    conventions.update_attributes(ds)
    return ds


def build_burst_id(lat: float, lon: float, relative_orbit: int) -> str:
    lat = int(round(lat * 10))
    lon = int(round(lon * 10))

    n_or_s = "N" if lat >= 0 else "S"
    e_or_w = "E" if lon >= 0 else "W"
    burst_id = f"R{relative_orbit:03}" f"-{n_or_s}{lat:03}" f"-{e_or_w}{lon:04}"
    return burst_id


def compute_burst_centres(
    gcp: xr.Dataset,
) -> T.Tuple[NT.NDArray[np.float_], NT.NDArray[np.float_]]:
    gcp_rolling = gcp.rolling(azimuth_time=2, min_periods=1)
    gc_az_win = gcp_rolling.construct(azimuth_time="az_win")
    centre = gc_az_win.mean(["az_win", "slant_range_time"])
    centre = centre.isel(azimuth_time=slice(1, None))
    return centre.latitude.values, centre.longitude.values


def open_dataset(
    product_urlpath: esa_safe.PathType,
    *,
    drop_variables: T.Optional[T.Tuple[str]] = None,
    group: T.Optional[str] = None,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
    fs: T.Optional[fsspec.AbstractFileSystem] = None,
) -> xr.Dataset:
    fs, manifest_path = get_fs_path(product_urlpath, fs)

    if fs.isdir(manifest_path):
        manifest_path = os.path.join(manifest_path, "manifest.safe")

    base_path = os.path.dirname(manifest_path)

    with fs.open(manifest_path) as file:
        product_attrs, product_files = esa_safe.parse_manifest_sentinel1(file)

    ancillary_data_paths = esa_safe.get_ancillary_data_paths(base_path, product_files)
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")

    groups = find_avalable_groups(ancillary_data_paths, product_attrs, fs=fs)

    if group is None:
        ds = open_root_dataset(product_attrs, groups)
    elif group not in groups:
        raise ValueError(
            f"Invalid group {group}, please select one of the following groups:"
            f"\n{list(groups.keys())}"
        )
    elif "/" not in group:
        ds = open_swath_dataset(
            manifest_path, groups[group]["measurement_path"], groups[group]["subgroups"]
        )
    else:
        subswath, subgroup = group.split("/", 1)
        if subgroup in METADATA_OPENERS:
            annotation_path = list(groups[group]["annotation_path"].values())[0]
            with fs.open(annotation_path) as annotation_file:
                ds = METADATA_OPENERS[subgroup](annotation_file)
        elif subgroup == "calibration":
            calibration_path = list(groups[group]["calibration_path"].values())[0]
            with fs.open(calibration_path) as calibration_path:
                ds = open_calibration_dataset(calibration_path)
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

        return open_dataset(filename_or_obj, drop_variables=drop_variables, group=group)

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
