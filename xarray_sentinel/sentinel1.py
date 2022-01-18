import os
import typing as T
import warnings

import fsspec
import numpy as np
import pandas as pd
import xarray as xr

from . import conventions, esa_safe


def open_calibration_dataset(calibration: esa_safe.PathType) -> xr.Dataset:
    calibration_vectors = esa_safe.parse_tag_list(
        calibration, ".//calibrationVector", "calibration"
    )

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
    data_vars = {
        "azimuth_time": ("line", [np.datetime64(dt) for dt in azimuth_time_list]),
        "sigmaNought": (("line", "pixel"), sigmaNought_list),
        "betaNought": (("line", "pixel"), betaNought_list),
        "gamma": (("line", "pixel"), gamma_list),
        "dn": (("line", "pixel"), dn_list),
    }
    coords = {"line": line_list, "pixel": pixel_list[0]}

    return xr.Dataset(data_vars=data_vars, coords=coords)


def open_coordinateConversion_dataset(annotation_path: esa_safe.PathType) -> xr.Dataset:
    coordinate_conversion = esa_safe.parse_tag(
        annotation_path, ".//coordinateConversionList"
    )

    gr0 = []
    sr0 = []
    azimuth_time = []
    slant_range_time = []
    srgrCoefficients: T.List[T.List[float]] = []
    grsrCoefficients: T.List[T.List[float]] = []
    for values in coordinate_conversion["coordinateConversion"]:
        sr0.append(values["sr0"])
        gr0.append(values["gr0"])
        azimuth_time.append(values["azimuthTime"])
        slant_range_time.append(values["slantRangeTime"])
        srgrCoefficients.append(
            [float(v) for v in values["srgrCoefficients"]["$"].split()]
        )
        grsrCoefficients.append(
            [float(v) for v in values["grsrCoefficients"]["$"].split()]
        )

    coords = {
        "azimuth_time": [np.datetime64(dt) for dt in azimuth_time],
        "degree": list(range(len(srgrCoefficients[0]))),
    }

    data_vars = {
        "gr0": ("azimuth_time", gr0),
        "sr0": ("azimuth_time", sr0),
        "slant_range_time": ("azimuth_time", slant_range_time),
        "srgr_coefficients": (("azimuth_time", "degree"), srgrCoefficients),
        "grsr_coefficients": (("azimuth_time", "degree"), grsrCoefficients),
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
    geolocation_grid_points = esa_safe.parse_tag_list(
        annotation, ".//geolocationGridPoint"
    )

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
    attitudes = esa_safe.parse_tag_list(annotation, ".//attitude")

    variables = ["q0", "q1", "q2", "q3", "wx", "wy", "wz", "pitch", "roll", "yaw"]
    azimuth_time: T.List[T.Any] = []
    data_vars: T.Dict[str, T.Any] = {var: ("azimuth_time", []) for var in variables}
    for attitude in attitudes:
        azimuth_time.append(attitude["time"])
        for var in variables:
            data_vars[var][1].append(attitude[var])

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={"azimuth_time": [np.datetime64(dt) for dt in azimuth_time]},
    )

    return ds


def open_orbit_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    orbits = esa_safe.parse_tag_list(annotation, ".//orbit")

    reference_system = orbits[0]["frame"]
    variables = ["position", "velocity"]
    data: T.Dict[str, T.List[T.Any]] = {var: [[], [], []] for var in variables}
    azimuth_time: T.List[T.Any] = []
    for orbit in orbits:
        azimuth_time.append(orbit["time"])
        data["position"][0].append(orbit["position"]["x"])
        data["position"][1].append(orbit["position"]["y"])
        data["position"][2].append(orbit["position"]["z"])
        data["velocity"][0].append(orbit["velocity"]["x"])
        data["velocity"][1].append(orbit["velocity"]["y"])
        data["velocity"][2].append(orbit["velocity"]["z"])
        if orbit["frame"] != reference_system:
            warnings.warn(
                "reference_system is not consistent in all the state vectors. "
            )
            reference_system = None

    position = xr.Variable(data=data["position"], dims=("axis", "azimuth_time"))  # type: ignore
    velocity = xr.Variable(data=data["velocity"], dims=("axis", "azimuth_time"))  # type: ignore

    attrs = {}
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})

    ds = xr.Dataset(
        data_vars={"position": position, "velocity": velocity},
        attrs=attrs,
        coords={
            "azimuth_time": [np.datetime64(dt) for dt in azimuth_time],
            "axis": [0, 1, 2],
        },
    )

    return ds


def open_dc_estimate_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    dc_estimates = esa_safe.parse_dc_estimate(annotation)

    azimuth_time = []
    t0 = []
    data_dc_poly = []
    for dc_estimate in dc_estimates:
        azimuth_time.append(dc_estimate["azimuthTime"])
        t0.append(dc_estimate["t0"])
        data_dc_poly.append(dc_estimate["dataDcPolynomial"])

    ds = xr.Dataset(
        data_vars={
            "t0": ("azimuth_time", t0),
            "data_dc_polynomial": (("azimuth_time", "degree"), data_dc_poly),
        },
        coords={
            "azimuth_time": [np.datetime64(at) for at in azimuth_time],
            "degree": list(range(len(data_dc_poly[0]))),
        },
    )
    return ds


def open_azimuth_fm_rate_dataset(annotation: esa_safe.PathOrFileType) -> xr.Dataset:
    azimuth_fm_rates = esa_safe.parse_azimuth_fm_rate(annotation)

    azimuth_time = []
    t0 = []
    azimuth_fm_rate_poly = []
    for azimuth_fm_rate in azimuth_fm_rates:
        azimuth_time.append(azimuth_fm_rate["azimuthTime"])
        t0.append(azimuth_fm_rate["t0"])
        azimuth_fm_rate_poly.append(azimuth_fm_rate["azimuthFmRatePolynomial"])

    ds = xr.Dataset(
        data_vars={
            "t0": ("azimuth_time", t0),
            "azimuth_fm_rate_polynomial": (
                ("azimuth_time", "degree"),
                azimuth_fm_rate_poly,
            ),
        },
        coords={
            "azimuth_time": [np.datetime64(at) for at in azimuth_time],
            "degree": list(range(len(azimuth_fm_rate_poly[0]))),
        },
    )
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
            for metadata_group in [
                "gcp",
                "orbit",
                "attitude",
                "dc_estimate",
                "azimuth_fm_rate",
            ]:
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
    measurement: esa_safe.PathType,
    annotation: esa_safe.PathType,
    chunks: T.Optional[T.Union[int, T.Dict[str, int]]] = None,
) -> xr.Dataset:
    image_information = esa_safe.parse_tag(annotation, ".//imageInformation")
    product_information = esa_safe.parse_tag(annotation, ".//productInformation")
    swath_timing = esa_safe.parse_tag(annotation, ".//swathTiming")

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
        freq=pd.Timedelta(azimuth_time_interval, "s"),
    ).values
    attrs = {
        "sar:center_frequency": product_information["radarFrequency"] / 10 ** 9,
    }

    number_of_bursts = swath_timing["burstList"]["@count"]
    if number_of_bursts:
        lines_per_burst = swath_timing["linesPerBurst"]
        attrs.update(
            {
                "azimuth_steering_rate": product_information["azimuthSteeringRate"],
                "number_of_bursts": number_of_bursts,
                "lines_per_burst": lines_per_burst,
            }
        )
        for burst_index, burst in enumerate(swath_timing["burstList"]["burst"]):
            first_azimuth_time_burst = burst["azimuthTime"]
            azimuth_time_burst = pd.date_range(
                start=first_azimuth_time_burst,
                periods=lines_per_burst,
                freq=pd.Timedelta(azimuth_time_interval, "s"),
            )
            azimuth_time[
                lines_per_burst * burst_index : lines_per_burst * (burst_index + 1)
            ] = azimuth_time_burst
        if chunks is None:
            # chunk at burst boundaries if dask is present
            try:
                import dask  # noqa

                chunks = {"y": lines_per_burst}
            except ModuleNotFoundError:
                pass

    arr = xr.open_dataarray(measurement, engine="rasterio", chunks=chunks)  # type: ignore
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


def find_bursts_index(
    pol_dataset: xr.Dataset,
    azimuth_anx_time: float,
    use_center: bool = False,
) -> int:
    lines_per_burst = pol_dataset.attrs["lines_per_burst"]
    anx_datetime = np.datetime64(pol_dataset.attrs["sat:anx_datetime"])
    azimuth_anx_time = pd.Timedelta(azimuth_anx_time, unit="s")
    if use_center:
        azimuth_anx_time_center = (
            pol_dataset.azimuth_time[lines_per_burst // 2 :: lines_per_burst]
            - anx_datetime
        )
        distance = abs(azimuth_anx_time_center - azimuth_anx_time)
    else:
        azimuth_anx_time_first_line = (
            pol_dataset.azimuth_time[::lines_per_burst] - anx_datetime
        )
        distance = abs(azimuth_anx_time_first_line - azimuth_anx_time)
    return distance.argmin().item()  # type: ignore


def crop_burst_dataset(
    pol_dataset: xr.Dataset,
    burst_index: T.Optional[int] = None,
    azimuth_anx_time: T.Optional[float] = None,
    use_center: bool = False,
) -> xr.Dataset:
    if (burst_index is not None) and (azimuth_anx_time is not None):
        raise TypeError(
            "only one keyword between 'burst_index' and 'azimuth_anx_time' must be defined"
        )

    if burst_index is None:
        if azimuth_anx_time is not None:
            burst_index = find_bursts_index(
                pol_dataset, azimuth_anx_time, use_center=use_center
            )
        else:
            raise TypeError(
                "one keyword between 'burst_index' and 'azimuth_anx_time' must be defined"
            )

    if burst_index < 0 or burst_index >= pol_dataset.attrs["number_of_bursts"]:
        raise IndexError(f"burst_index={burst_index} out of bounds")

    lines_per_burst = pol_dataset.attrs["lines_per_burst"]
    ds = pol_dataset.sel(
        line=slice(
            lines_per_burst * burst_index, lines_per_burst * (burst_index + 1) - 1
        )
    )

    anx_datetime = np.datetime64(pol_dataset.attrs["sat:anx_datetime"])
    burst_azimuth_anx_times = ds.azimuth_time - anx_datetime
    ds.attrs["azimuth_anx_time"] = (
        burst_azimuth_anx_times / np.timedelta64(1, "s")
    ).item(0)
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
) -> T.Tuple[T.List[float], T.List[float]]:
    gcp_rolling = gcp.rolling(azimuth_time=2, min_periods=1)
    gc_az_win = gcp_rolling.construct(azimuth_time="az_win")
    centre = gc_az_win.mean(["az_win", "slant_range_time"])
    centre = centre.isel(azimuth_time=slice(1, None))
    return centre.latitude.values.tolist(), centre.longitude.values.tolist()


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


def open_sentinel1_dataset(
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
        else:
            subswath, pol, metadata = group.split("/", 2)
            with fs.open(groups[group]) as file:
                ds = METADATA_OPENERS[metadata](file)

    product_attrs["group"] = absgroup
    if len(subgroups):
        product_attrs["subgroups"] = subgroups
    ds.attrs.update(product_attrs)  # type: ignore

    if group.count("/") == 1 and burst_index is not None:
        ds = crop_burst_dataset(ds, burst_index=burst_index)

    conventions.update_attributes(ds, group=metadata)

    return ds


METADATA_OPENERS = {
    "gcp": open_gcp_dataset,
    "orbit": open_orbit_dataset,
    "attitude": open_attitude_dataset,
    "dc_estimate": open_dc_estimate_dataset,
    "azimuth_fm_rate": open_azimuth_fm_rate_dataset,
    "calibration": open_calibration_dataset,
}
