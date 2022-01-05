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
        azimuth_time_list.append(np.datetime64(vector["azimuthTime"]))
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
    srgrCoefficients: T.List[NT.NDArray[np.float_]] = []
    grsrCoefficients: T.List[NT.NDArray[np.float_]] = []
    for values in coordinateConversionList["coordinateConversion"]:
        sr0.append(values["sr0"])
        gr0.append(values["gr0"])
        azimuthTime.append(values["azimuthTime"])
        slantRangeTime.append(values["slantRangeTime"])
        srgrCoefficients.append(
            np.fromstring(values["srgrCoefficients"]["$"], dtype=float, sep=" ")
        )
        grsrCoefficients.append(
            np.fromstring(values["grsrCoefficients"]["$"], dtype=float, sep=" ")
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
        data_vars=data_vars,
        coords={"time": [np.datetime64(dt) for dt in time]},
    )
    ds = ds.rename({"time": "azimuth_time"})
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
        coords={"time": [np.datetime64(dt) for dt in time], "axis": [0, 1, 2]},
    )
    ds = ds.rename({"time": "azimuth_time"})
    return ds


def find_avalable_groups(
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]],
    product_attrs: T.Dict[str, T.Any],
    fs: fsspec.AbstractFileSystem = fsspec.filesystem("file"),
) -> T.Dict[str, str]:
    groups: T.Dict[str, str] = {}
    for subswath_id, subswath_data_path in ancillary_data_paths.items():
        for pol_id, pol_data_paths in subswath_data_path.items():
            try:
                with fs.open(pol_data_paths["s1Level1ProductSchema"]):
                    pass
            except FileNotFoundError:
                continue
            groups[subswath_id] = ""
            groups[f"{subswath_id}/{pol_id}"] = pol_data_paths["s1Level1ProductSchema"]
            for metadata_group in ["gcp", "orbit", "attitude"]:
                groups[f"{subswath_id}/{pol_id}/{metadata_group}"] = pol_data_paths[
                    "s1Level1ProductSchema"
                ]

            try:
                with fs.open(pol_data_paths["s1Level1CalibrationSchema"]):
                    pass
            except FileNotFoundError:
                continue
            groups[f"{subswath_id}/{pol_id}/calibration"] = pol_data_paths[
                "s1Level1CalibrationSchema"
            ]

    return groups


def open_pol_dataset(
    measurement_path: esa_safe.PathType,
    annotation_path: esa_safe.PathType,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    image_information = esa_safe.parse_image_information(annotation_path)
    product_information = esa_safe.parse_product_information(annotation_path)
    swath_timing = esa_safe.parse_swath_timing(annotation_path)

    number_of_samples = image_information["numberOfSamples"]
    first_slant_range_time = image_information["slantRangeTime"]
    slant_range_sampling = 1 / product_information["rangeSamplingRate"]
    slant_range_time = np.linspace(
        first_slant_range_time,
        first_slant_range_time + slant_range_sampling * (number_of_samples - 1),
        number_of_samples,
    )

    number_of_lines = image_information["numberOfLines"]
    first_azimuth_time = image_information["productFirstLineUtcTime"]
    azimuth_time_interval = image_information["azimuthTimeInterval"]
    azimuth_time = pd.date_range(
        start=first_azimuth_time,
        periods=number_of_lines,
        freq=pd.to_timedelta(azimuth_time_interval, "s"),
    ).values
    attrs = {}

    number_of_bursts = swath_timing["burstList"]["@count"]
    if number_of_bursts:
        lines_per_burst = swath_timing["linesPerBurst"]
        attrs.update(
            {
                "number_of_bursts": number_of_bursts,
                "lines_per_burst": lines_per_burst,
            }
        )
        for burst_index, burst in enumerate(swath_timing["burstList"]["burst"]):
            first_azimuth_time_burst = burst["azimuthTime"]
            azimuth_time_burst = pd.date_range(
                start=first_azimuth_time_burst,
                periods=lines_per_burst,
                freq=pd.to_timedelta(azimuth_time_interval, "s"),
            )
            azimuth_time[
                lines_per_burst * burst_index : lines_per_burst * (burst_index + 1)
            ] = azimuth_time_burst
        if chunks is None:
            chunks = {"y": lines_per_burst}

    arr = rioxarray.open_rasterio(measurement_path, chunks=chunks)
    arr = arr.squeeze("band").drop_vars(["band", "spatial_ref"])
    arr = arr.rename({"y": "line", "x": "pixel"})
    arr = arr.assign_coords(
        {
            "pixel": np.arange(0, arr["pixel"].size, dtype=int),
            "line": np.arange(0, arr["line"].size, dtype=int),
            "slant_range_time": ("pixel", slant_range_time),
            "azimuth_time": ("line", azimuth_time),
        }
    )

    if number_of_bursts == 0:
        arr = arr.swap_dims({"line": "azimuth_time", "pixel": "slant_range_time"})

    return xr.Dataset(attrs=attrs, data_vars={"measurement": arr})


def crop_burst_dataset(pol_dataset: xr.Dataset, burst_index: int) -> xr.Dataset:
    if burst_index < 0 or burst_index >= pol_dataset.attrs["number_of_bursts"]:
        raise IndexError(f"{burst_index=} out of bounds")

    lines_per_burst = pol_dataset.attrs["lines_per_burst"]
    ds = pol_dataset.sel(
        line=slice(
            lines_per_burst * burst_index, lines_per_burst * (burst_index + 1) - 1
        )
    )
    ds = ds.swap_dims({"line": "azimuth_time", "pixel": "slant_range_time"})
    ds.attrs["burst_index"] = burst_index

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


def normalise_group(group: T.Optional[str]) -> T.Tuple[str, T.Optional[int]]:
    if group is None:
        group = ""
    if group.startswith("/"):
        group = group[1:]
    burst_index = None
    parent_group, _, last_name = group.rpartition("/")
    if parent_group.count("/") == 1 and last_name.isnumeric():
        burst_index = int(last_name)
        group = parent_group
    return group, burst_index


def open_dataset(
    product_urlpath: esa_safe.PathType,
    *,
    drop_variables: T.Optional[T.Tuple[str]] = None,
    group: T.Optional[str] = None,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
    fs: T.Optional[fsspec.AbstractFileSystem] = None,
) -> xr.Dataset:
    group, burst_index = normalise_group(group)
    absgroup = f"/{group}"

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

    if group != "" and group not in groups:
        raise ValueError(
            f"Invalid group {group!r}, please select one of the following groups:"
            f"\n{list(groups.keys())}"
        )

    metadata = ""

    if group == "":
        ds = xr.Dataset()
        subgroups = list(groups)
    else:
        subgroups = [
            g[len(group) + 1 :] for g in groups if g.startswith(group) and g != group
        ]

        if "/" not in group:
            ds = xr.Dataset()
        elif group.count("/") == 1:
            subswath, pol = group.split("/", 1)
            ds = open_pol_dataset(
                ancillary_data_paths[subswath][pol]["s1Level1MeasurementSchema"],
                ancillary_data_paths[subswath][pol]["s1Level1ProductSchema"],
                chunks=chunks,
            )
            if burst_index is not None:
                ds = crop_burst_dataset(ds, burst_index=burst_index)
        else:
            subswath, pol, metadata = group.split("/", 2)
            with fs.open(groups[group]) as file:
                ds = METADATA_OPENERS[metadata](file)

    product_attrs["group"] = absgroup
    if len(subgroups):
        product_attrs["subgroups"] = subgroups
    ds.attrs.update(product_attrs)  # type: ignore
    conventions.update_attributes(ds, group=metadata)

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
    "orbit": open_orbit_dataset,
    "attitude": open_attitude_dataset,
    "calibration": open_calibration_dataset,
}
