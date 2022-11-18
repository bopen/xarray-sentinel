"""Map Sentinel-1 data products to xarray.

References:
  - Sentinel-1 document library:
    https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar/document-library
  - Sentinel-1 Product Specification v3.9 07 May 2021 S1-RS-MDA-52-7441-3-9 documenting IPF 3.40
    https://sentinel.esa.int/documents/247904/1877131/S1-RS-MDA-52-7441-3-9-2_Sentinel-1ProductSpecification.pdf
  - Sentinel-1 Product Specification v3.7 27 February 2020 S1-RS-MDA-52-7441 documenting IPF 3.30
    https://sentinel.esa.int/documents/247904/1877131/Sentinel-1-Product-Specification
"""
from __future__ import annotations

import os
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar

import fsspec
import numpy as np
import numpy.typing as npt
import pandas as pd
import rasterio
import xarray as xr

from . import conventions, esa_safe

SPEED_OF_LIGHT = 299_792_458  # m / s
ONE_SECOND = np.timedelta64(1, "s")


DataArrayOrDataset = TypeVar("DataArrayOrDataset", xr.DataArray, xr.Dataset)


def get_fs_path(
    urlpath_or_path: esa_safe.PathType,
    fs: Optional[fsspec.AbstractFileSystem] = None,
    storage_options: Optional[Dict[str, Any]] = None,
) -> Tuple[fsspec.AbstractFileSystem, str]:
    if fs is not None and storage_options is not None:
        raise TypeError("only one of 'fs' and 'storage_options' can be not None")

    if fs is None:
        fs, _, paths = fsspec.get_fs_token_paths(
            urlpath_or_path, storage_options=storage_options
        )
        if len(paths) == 0:
            raise ValueError(f"file or object not found {urlpath_or_path!r}")
        elif len(paths) > 1:
            raise ValueError(f"multiple files or objects found {urlpath_or_path!r}")
        path = paths[0]
    else:
        path = str(urlpath_or_path)

    if fs.isdir(path):
        path = os.path.join(path, "manifest.safe")

    return fs, path


def normalise_group(group: Optional[str]) -> Tuple[str, Optional[int]]:
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


def open_calibration_dataset(
    calibration: esa_safe.PathType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    calibration_vectors = esa_safe.parse_tag_as_list(
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
        pixel = np.fromstring(vector["pixel"]["$"], dtype=int, sep=" ")
        pixel_list.append(pixel)
        sigmaNought = np.fromstring(
            vector["sigmaNought"]["$"], dtype=np.float32, sep=" "
        )
        sigmaNought_list.append(sigmaNought)
        betaNought = np.fromstring(vector["betaNought"]["$"], dtype=np.float32, sep=" ")
        betaNought_list.append(betaNought)
        gamma = np.fromstring(vector["gamma"]["$"], dtype=np.float32, sep=" ")
        gamma_list.append(gamma)
        dn = np.fromstring(vector["dn"]["$"], dtype=np.float32, sep=" ")
        dn_list.append(dn)

    pixel = np.array(pixel_list)
    if (pixel - pixel[0]).any():
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

    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def open_noise_range_dataset(
    noise: esa_safe.PathType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    noise_vectors = esa_safe.parse_tag_as_list(noise, ".//noiseRangeVector", "noise")

    azimuth_time_list = []
    pixel_list = []
    line_list = []
    noiseRangeLut_list = []
    for vector in noise_vectors:
        azimuth_time_list.append(vector["azimuthTime"])
        line_list.append(vector["line"])
        pixel = np.fromstring(vector["pixel"]["$"], dtype=int, sep=" ")
        pixel_list.append(pixel)
        noiseRangeLut = np.fromstring(
            vector["noiseRangeLut"]["$"], dtype=np.float32, sep=" "
        )
        noiseRangeLut_list.append(noiseRangeLut)

    pixel = np.array(pixel_list)
    if (pixel - pixel[0]).any():
        raise ValueError(
            "Unable to organise noise vectors in a regular line-pixel grid"
        )
    data_vars = {
        "azimuth_time": ("line", [np.datetime64(dt) for dt in azimuth_time_list]),
        "noiseRangeLut": (("line", "pixel"), noiseRangeLut_list),
    }
    coords = {"line": line_list, "pixel": pixel_list[0]}

    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def open_noise_azimuth_dataset(
    noise: esa_safe.PathType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    noise_vectors = esa_safe.parse_tag_as_list(noise, ".//noiseAzimuthVector", "noise")

    first_range_sample = []
    line_list = []
    noiseAzimuthLut_list = []
    for vector in noise_vectors:
        first_range_sample.append(vector["firstRangeSample"])
        line = np.fromstring(vector["line"]["$"], dtype=int, sep=" ")
        line_list.append(line)
        noiseAzimuthLut = np.fromstring(
            vector["noiseAzimuthLut"]["$"], dtype=np.float32, sep=" "
        )
        noiseAzimuthLut_list.append(noiseAzimuthLut)

    # BROKEN: GRDs have line and noiseAzimuthLut of different size, we take the first one
    data_vars = {}
    coords = {}
    if first_range_sample:
        data_vars["noiseAzimuthLut"] = ("line", noiseAzimuthLut_list[0])
        coords["line"] = line_list[0]

    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def open_coordinate_conversion_dataset(
    annotation_path: esa_safe.PathType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    coordinate_conversion = esa_safe.parse_tag_as_list(
        annotation_path, ".//coordinateConversionList/coordinateConversion"
    )
    if len(coordinate_conversion) == 0:
        raise TypeError("coordinateConversion tag not present in annotations")

    gr0 = []
    sr0 = []
    azimuth_time = []
    slant_range_time = []
    srgrCoefficients: List[List[float]] = []
    grsrCoefficients: List[List[float]] = []
    for values in coordinate_conversion:
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

    coords: Dict[str, Any] = {}
    data_vars: Dict[str, Any] = {}
    coords["azimuth_time"] = [np.datetime64(dt) for dt in azimuth_time]
    coords["degree"] = list(range(len(srgrCoefficients[0])))

    data_vars["gr0"] = ("azimuth_time", gr0)
    data_vars["sr0"] = ("azimuth_time", sr0)
    data_vars["slant_range_time"] = ("azimuth_time", slant_range_time)
    data_vars["srgrCoefficients"] = (("azimuth_time", "degree"), srgrCoefficients)
    data_vars["grsrCoefficients"] = (("azimuth_time", "degree"), grsrCoefficients)

    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def is_clockwise(poly: List[Tuple[float, float]]) -> bool:
    start = np.array(poly[0])
    return float(np.cross(poly[1] - start, poly[2] - start)) < 0


def open_gcp_dataset(
    annotation: esa_safe.PathOrFileType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    geolocation_grid_points = esa_safe.parse_tag_as_list(
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
        "latitude": (dims, np.full(shape, np.nan), attrs),
        "longitude": (dims, np.full(shape, np.nan), attrs),
        "height": (dims, np.full(shape, np.nan), attrs),
        "incidenceAngle": (dims, np.full(shape, np.nan), attrs),
        "elevationAngle": (dims, np.full(shape, np.nan), attrs),
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
        attrs=attrs,
    )

    footprint = get_footprint_linestring(ds.azimuth_time, ds.slant_range_time, ds)
    geospatial_attrs = make_geospatial_attributes(footprint)
    ds.attrs.update(geospatial_attrs)

    return ds


def get_footprint_linestring(
    azimuth_time: xr.DataArray,
    slant_range_time: xr.DataArray,
    gcp: xr.Dataset,
    method: xr.core.types.InterpOptions = "linear",
    kwargs: Dict[str, Any] = {"fill_value": "extrapolate"},
) -> List[Tuple[float, float]]:
    azimuth_time_mm = [azimuth_time.min(), azimuth_time.max()]
    slant_range_time_mm = [slant_range_time.min(), slant_range_time.max()]

    footprint = []
    for j, i in [(0, 0), (1, 0), (1, 1), (0, 1)]:
        lat = float(
            gcp["latitude"].interp(
                azimuth_time=azimuth_time_mm[j],
                slant_range_time=slant_range_time_mm[i],
                method=method,
                kwargs=kwargs,
            )
        )
        lon = float(
            gcp["longitude"].interp(
                azimuth_time=azimuth_time_mm[j],
                slant_range_time=slant_range_time_mm[i],
                method=method,
                kwargs=kwargs,
            )
        )
        footprint.append((lon, lat))

    # check that the poly as the correct orientation
    if is_clockwise(footprint):
        footprint = footprint[::-1]

    # close the polygon
    footprint.append(footprint[0])

    return footprint


def make_geospatial_attributes(
    footprint: Sequence[Tuple[float, float]]
) -> Dict[str, Any]:
    wkt = "POLYGON((" + ",".join(f"{y} {x}" for y, x in footprint) + "))"
    geospatial_attrs = {
        "geospatial_bounds": wkt,
        "geospatial_lat_min": min(lat for _, lat in footprint),
        "geospatial_lat_max": max(lat for _, lat in footprint),
        "geospatial_lon_min": min(lon for lon, _ in footprint),
        "geospatial_lon_max": max(lon for lon, _ in footprint),
    }
    return geospatial_attrs


def open_attitude_dataset(
    annotation: esa_safe.PathOrFileType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    attitudes = esa_safe.parse_tag_as_list(annotation, ".//attitude")

    variables = ["q0", "q1", "q2", "q3", "wx", "wy", "wz", "pitch", "roll", "yaw"]
    azimuth_time: List[Any] = []
    data_vars: Dict[str, Any]
    data_vars = {var: ("azimuth_time", [], attrs) for var in variables}
    for attitude in attitudes:
        azimuth_time.append(attitude["time"])
        for var in variables:
            data_vars[var][1].append(attitude[var])

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={"azimuth_time": [np.datetime64(dt) for dt in azimuth_time]},
        attrs=attrs,
    )

    return ds


def make_orbit(
    azimuth_time: List[Any],
    positions: List[List[Any]],
    velocities: List[List[Any]],
    attrs: Dict[str, Any] = {},
) -> xr.Dataset:
    position = xr.Variable(data=positions, dims=("axis", "azimuth_time"))  # type: ignore
    velocity = xr.Variable(data=velocities, dims=("axis", "azimuth_time"))  # type: ignore

    ds = xr.Dataset(
        data_vars={"position": position, "velocity": velocity},
        attrs=attrs,
        coords={
            "azimuth_time": [np.datetime64(dt) for dt in azimuth_time],
            "axis": [0, 1, 2],
        },
    )
    for data_var in ds.data_vars:
        ds[data_var].attrs = attrs

    return ds


def open_orbit_dataset(
    annotation: esa_safe.PathOrFileType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    orbits = esa_safe.parse_tag_as_list(annotation, ".//orbit")

    attrs = attrs.copy()
    reference_system = orbits[0]["frame"]
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})

    azimuth_times: List[Any] = []
    positions: List[List[Any]] = [[], [], []]
    velocities: List[List[Any]] = [[], [], []]
    for orbit in orbits:
        azimuth_times.append(orbit["time"])
        positions[0].append(orbit["position"]["x"])
        positions[1].append(orbit["position"]["y"])
        positions[2].append(orbit["position"]["z"])
        velocities[0].append(orbit["velocity"]["x"])
        velocities[1].append(orbit["velocity"]["y"])
        velocities[2].append(orbit["velocity"]["z"])
        if orbit["frame"] != reference_system:
            warnings.warn(
                "reference_system is not consistent in all the state vectors. "
            )
            reference_system = None

    return make_orbit(azimuth_times, positions, velocities, attrs)


def open_dc_estimate_dataset(
    annotation: esa_safe.PathOrFileType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    dc_estimates = esa_safe.parse_tag_as_list(annotation, ".//dcEstimate")

    azimuth_time = []
    t0 = []
    data_dc_poly = []
    for dc_estimate in dc_estimates:
        azimuth_time.append(dc_estimate["azimuthTime"])
        t0.append(dc_estimate["t0"])
        data_dc_poly.append(
            [float(c) for c in dc_estimate["dataDcPolynomial"]["$"].split()]
        )

    ds = xr.Dataset(
        data_vars={
            "t0": ("azimuth_time", t0, attrs),
            "data_dc_polynomial": (("azimuth_time", "degree"), data_dc_poly, attrs),
        },
        coords={
            "azimuth_time": [np.datetime64(at) for at in azimuth_time],
            "degree": list(range(len(data_dc_poly[0]))),
        },
        attrs=attrs,
    )
    return ds


def open_azimuth_fm_rate_dataset(
    annotation: esa_safe.PathOrFileType, attrs: Dict[str, Any] = {}
) -> xr.Dataset:
    azimuth_fm_rates = esa_safe.parse_tag_as_list(annotation, ".//azimuthFmRate")

    azimuth_time = []
    t0 = []
    azimuth_fm_rate_poly = []
    for azimuth_fm_rate in azimuth_fm_rates:
        azimuth_time.append(azimuth_fm_rate["azimuthTime"])
        t0.append(azimuth_fm_rate["t0"])
        azimuth_fm_rate_poly.append(
            [float(c) for c in azimuth_fm_rate["azimuthFmRatePolynomial"]["$"].split()]
        )

    ds = xr.Dataset(
        data_vars={
            "t0": (
                "azimuth_time",
                t0,
                attrs,
            ),
            "azimuth_fm_rate_polynomial": (
                ("azimuth_time", "degree"),
                azimuth_fm_rate_poly,
                attrs,
            ),
        },
        coords={
            "azimuth_time": [np.datetime64(at) for at in azimuth_time],
            "degree": list(range(len(azimuth_fm_rate_poly[0]))),
        },
        attrs=attrs,
    )
    return ds


def find_available_groups(
    product_files: Dict[str, Tuple[str, str, str, str, str]],
    product_path: str,
    check_files_exist: bool = False,
    fs: fsspec.AbstractFileSystem = fsspec.filesystem("file"),
) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for path, (type, _, swath, polarization, _) in product_files.items():
        swath_pol_group = f"{swath}/{polarization}".upper()
        abspath = os.path.join(product_path, os.path.normpath(path))
        if check_files_exist:
            if not fs.exists(abspath):
                continue
        if type == "s1Level1ProductSchema":
            groups[swath.upper()] = [""]
            groups[swath_pol_group] = [abspath] + groups.get(swath_pol_group, [])
            for metadata_group in [
                "orbit",
                "attitude",
                "azimuth_fm_rate",
                "dc_estimate",
                "gcp",
                "coordinate_conversion",
            ]:
                groups[f"{swath_pol_group}/{metadata_group}"] = [abspath]
        elif type == "s1Level1CalibrationSchema":
            groups[f"{swath_pol_group}/calibration"] = [abspath]
        elif type == "s1Level1NoiseSchema":
            groups[f"{swath_pol_group}/noise_range"] = [abspath]
            groups[f"{swath_pol_group}/noise_azimuth"] = [abspath]
        elif type == "s1Level1MeasurementSchema":
            groups[swath_pol_group] = [abspath] + groups.get(swath_pol_group, [])

    return groups


def open_rasterio_dataarray(
    measurement: esa_safe.PathOrFileType,
    fs: Optional[fsspec.AbstractFileSystem],
    chunks: Optional[Dict[str, int]],
) -> xr.DataArray:
    # fsspec needs rasterio >= 1.3.0, but we allow earlier rasterio versions for local files
    if fs is None or isinstance(fs, fsspec.implementations.local.LocalFileSystem):
        try:
            arr = xr.open_dataarray(measurement, engine="rasterio", chunks=chunks)  # type: ignore
        except rasterio.RasterioIOError as ex:
            if "No such file" in str(ex):
                raise FileNotFoundError(str(ex))
            raise
    else:
        # FIXME: rioxarray / rasterio do not support opening a file object any more, so
        #   full fsspec support via `fs.open(measurement)` is now broken and we fall back
        #   to hope that rasterio remote protocols works with fsspec urlpaths
        maybe_rasterio_urlpath = fs.unstrip_protocol(measurement)
        arr = xr.open_dataarray(
            maybe_rasterio_urlpath, engine="rasterio", chunks=chunks
        )
    return arr


def make_azimuth_time(
    product_first_line_utc_time: str,
    product_last_line_utc_time: str,
    number_of_lines: int,
) -> npt.NDArray[np.datetime64]:
    azimuth_time = pd.date_range(
        start=product_first_line_utc_time,
        end=product_last_line_utc_time,
        periods=number_of_lines,
    )
    return azimuth_time.values  # type: ignore


def open_pol_dataset(
    measurement: esa_safe.PathOrFileType,
    annotation: esa_safe.PathOrFileType,
    fs: Optional[fsspec.AbstractFileSystem] = None,
    attrs: Dict[str, Any] = {},
    gcp: Optional[xr.Dataset] = None,
) -> xr.Dataset:

    product_information = esa_safe.parse_tag(annotation, ".//productInformation")
    image_information = esa_safe.parse_tag(annotation, ".//imageInformation")
    swath_timing = esa_safe.parse_tag(annotation, ".//swathTiming")

    number_of_samples = image_information["numberOfSamples"]
    range_sampling_rate = product_information["rangeSamplingRate"]

    product_first_line_utc_time = image_information["productFirstLineUtcTime"]
    product_last_line_utc_time = image_information["productLastLineUtcTime"]
    number_of_lines = image_information["numberOfLines"]
    azimuth_time_interval = image_information["azimuthTimeInterval"]
    number_of_bursts = swath_timing["burstList"]["@count"]
    image_slant_range_time = image_information["slantRangeTime"]
    range_pixel_spacing = image_information["rangePixelSpacing"]

    attrs = attrs.copy()
    attrs.update(
        {
            "radar_frequency": product_information["radarFrequency"] / 10**9,
            "ascending_node_time": image_information["ascendingNodeTime"],
            "azimuth_pixel_spacing": image_information["azimuthPixelSpacing"],
            "range_pixel_spacing": range_pixel_spacing,
            "product_first_line_utc_time": product_first_line_utc_time,
            "product_last_line_utc_time": product_last_line_utc_time,
            "azimuth_time_interval": azimuth_time_interval,
            "image_slant_range_time": image_slant_range_time,
            "range_sampling_rate": range_sampling_rate,
            "incidence_angle_mid_swath": image_information["incidenceAngleMidSwath"],
        }
    )
    encoding = {}
    swap_dims = {}
    chunks: Optional[Dict[str, int]] = None

    azimuth_time = make_azimuth_time(
        product_first_line_utc_time,
        product_last_line_utc_time,
        number_of_lines,
    )
    if number_of_bursts == 0:
        swap_dims = {"line": "azimuth_time", "pixel": "slant_range_time"}
    else:
        if "burstId" in swath_timing["burstList"]["burst"][0]:
            burst_ids = []
            for burst in swath_timing["burstList"]["burst"]:
                burst_ids.append(burst["burstId"]["$"])
            attrs["burst_ids"] = burst_ids
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

        # chunk at burst boundaries if dask is present
        try:
            import dask  # noqa

            encoding["preferred_chunks"] = {"line": lines_per_burst}
            chunks = {}
        except ModuleNotFoundError:
            pass

    coords = {
        "pixel": np.arange(0, number_of_samples, dtype=int),
        "line": np.arange(0, number_of_lines, dtype=int),
        # set "units" explicitly as CF conventions don't support "nanoseconds".
        # See: https://github.com/pydata/xarray/issues/4183#issuecomment-685200043
        "azimuth_time": (
            "line",
            azimuth_time,
            {},
            {"units": f"microseconds since {azimuth_time[0]}"},
        ),
    }

    if product_information["projection"] == "Slant Range":
        slant_range_time = np.linspace(
            image_slant_range_time,
            image_slant_range_time + (number_of_samples - 1) / range_sampling_rate,
            number_of_samples,
        )
        coords["slant_range_time"] = ("pixel", slant_range_time)
    elif product_information["projection"] == "Ground Range":
        ground_range = np.linspace(
            0,
            range_pixel_spacing * (number_of_samples - 1),
            number_of_samples,
        )
        coords["ground_range"] = ("pixel", ground_range)
        swap_dims = {"line": "azimuth_time", "pixel": "ground_range"}
    else:
        raise ValueError(f"unknown projection {product_information['projection']}")

    arr = open_rasterio_dataarray(measurement, fs, chunks)

    # clear the encoding as many GeoTIFF details are inconpatible with the CF conventions
    arr.encoding.clear()

    arr = arr.squeeze("band").drop_vars(["band", "spatial_ref"])
    arr = arr.rename({"y": "line", "x": "pixel"})
    arr = arr.assign_coords(coords)
    arr = arr.swap_dims(swap_dims)

    if gcp:
        attrs.update(gcp.attrs)

    arr.attrs.update(attrs)
    arr.encoding.update(encoding)

    return xr.Dataset(attrs=attrs, data_vars={"measurement": arr})


def find_bursts_index(
    pol_dataset: DataArrayOrDataset,
    azimuth_anx_seconds: float,
    use_center: bool = False,
) -> int:
    lines_per_burst = pol_dataset.attrs["lines_per_burst"]
    anx_datetime = np.datetime64(pol_dataset.attrs["ascending_node_time"])
    azimuth_anx_time = pd.Timedelta(azimuth_anx_seconds, unit="s")
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
    pol_dataset: DataArrayOrDataset,
    burst_index: Optional[int] = None,
    azimuth_anx_time: Optional[float] = None,
    use_center: bool = False,
    burst_id: Optional[int] = None,
    gcp: Optional[xr.Dataset] = None,
) -> DataArrayOrDataset:
    """Return the measurement dataset cropped to the selected burst.

    Only one keyword between 'burst_index' and 'azimuth_anx_time' and 'burst_id' must be defined.

    :param xr.Dataset pol_dataset: measurement dataset
    :param int burst_index: burst index can take values from 1 to the number of bursts
    :param float azimuth_anx_time: azimuth anx time of first line of the bursts
    To use the center instead of the first line, set `use_center=True`
    :param bool use_center: If `True`, it uses the azimuth anx time as a reference for
    the burst center instead of the first line
    :param int burst_id: for product processed with Sentinel-1 IPF version 3.40 or higher,
    the burst can be selected using the relative burst id.
    """
    burst_definitions = (
        (burst_index is not None)
        + (azimuth_anx_time is not None)
        + (burst_id is not None)
    )
    if burst_definitions > 1:
        raise TypeError(
            "only one keyword between 'burst_index' and 'azimuth_anx_time' and 'burst_id' must be defined"
        )

    if burst_index is None:
        if azimuth_anx_time is not None:
            burst_index = find_bursts_index(
                pol_dataset, azimuth_anx_time, use_center=use_center
            )
        elif burst_id is not None:
            burst_ids = pol_dataset.attrs.get("burst_ids")
            if burst_ids is None:
                raise TypeError(
                    "'burst_ids' list can't be found in product attributes, "
                    "probably Sentinel-1 IPF processor version is older than 3.40"
                )
            try:
                burst_index = burst_ids.index(burst_id)
            except ValueError:
                raise KeyError(f"{burst_id=} not found in product {burst_ids=}")
        else:
            raise TypeError(
                "one keyword between 'burst_index' and 'azimuth_anx_time' must be defined"
            )

    if burst_index < 0 or burst_index >= pol_dataset.attrs["number_of_bursts"]:
        raise IndexError(f"{burst_index=} out of bounds")

    lines_per_burst = pol_dataset.attrs["lines_per_burst"]
    ds = pol_dataset.sel(
        line=slice(
            lines_per_burst * burst_index, lines_per_burst * (burst_index + 1) - 1
        )
    )

    ds = ds.swap_dims({"line": "azimuth_time", "pixel": "slant_range_time"})

    anx_datetime = np.datetime64(pol_dataset.attrs["ascending_node_time"])
    burst_azimuth_anx_time = ds.azimuth_time.values[0] - anx_datetime
    ds.attrs["azimuth_anx_time"] = burst_azimuth_anx_time / ONE_SECOND
    ds.attrs["burst_index"] = burst_index
    ds.attrs.pop("subgroups", None)

    if gcp is not None:
        footprint = get_footprint_linestring(ds.azimuth_time, ds.slant_range_time, gcp)
        geospatial_attrs = make_geospatial_attributes(footprint)
        ds.attrs.update(geospatial_attrs)

    if "burst_ids" in ds.attrs:
        ds.attrs["burst_id"] = ds.attrs["burst_ids"][burst_index]
        _ = ds.attrs.pop("burst_ids")

    return ds


def mosaic_slc_iw(
    slc_iw_image: DataArrayOrDataset, crop: int = 90
) -> DataArrayOrDataset:
    bursts = []
    for i in range(slc_iw_image.attrs["number_of_bursts"]):
        burst = crop_burst_dataset(slc_iw_image, burst_index=i)
        bursts.append(burst.isel(azimuth_time=slice(crop, -crop)))
    return xr.concat(bursts, dim="azimuth_time")


def calibrate_amplitude(
    digital_number: xr.DataArray,
    calibration_lut: xr.DataArray,
    **kwargs: Any,
) -> xr.DataArray:
    """Return the calibrated amplitude. The calibration is done using the calibration LUT in the product metadata.

    :param digital_number: digital numbers to be calibrated
    :param calibration_lut: calibration LUT (sigmaNought, betaNought or gamma).

    The LUT can be opened using the measurement sub-group `calibration`
    """
    calibration_lut_mean = calibration_lut.mean()
    if np.allclose(calibration_lut_mean, calibration_lut, **kwargs):
        calibration: xr.DataArray = calibration_lut_mean.astype(np.float32)
    else:
        calibration = calibration_lut.interp(
            line=digital_number.line,
            pixel=digital_number.pixel,
        ).astype(np.float32)
        if digital_number.chunks is not None:
            calibration = calibration.chunk(digital_number.chunksizes)
    amplitude = digital_number / calibration
    amplitude.attrs.update(digital_number.attrs)
    try:
        lut_name = calibration_lut.attrs["long_name"].partition("calibration LUT")[0]
        amplitude.attrs["long_name"] = f"amplitude for {lut_name}".strip()
        amplitude.attrs["units"] = calibration.attrs["units"]
    except KeyError:
        pass
    return amplitude


def calibrate_intensity(
    digital_number: xr.DataArray,
    calibration_lut: xr.DataArray,
    as_db: bool = False,
    min_db: Optional[float] = -40.0,
    **kwargs: Any,
) -> xr.DataArray:
    """Return the calibrated intensity. The calibration is done using the calibration LUT in the product metadata.

    :param digital_number: digital numbers to be calibrated
    :param calibration_lut: calibration LUT (sigmaNought, betaNought or gamma).
    The LUT can be opened using the measurement sub-group `calibration`.
    :param as_db: if True, returns the data in db
    :param min_db: minimal value in db, to avoid infinity values.
    """
    amplitude = calibrate_amplitude(digital_number, calibration_lut, **kwargs)
    intensity = abs(amplitude) ** 2
    if as_db:
        intensity = 10.0 * np.log10(intensity)  # type: ignore
        if min_db is not None:
            intensity = np.maximum(intensity, min_db)  # type: ignore
        intensity.attrs.update(amplitude.attrs)
        intensity.attrs["units"] = "dB"
    else:
        intensity.attrs.update(amplitude.attrs)
        intensity.attrs["units"] = "m2 m-2"
    try:
        lut_name = amplitude.attrs["long_name"].partition("amplitude for ")[2]
        intensity.attrs["long_name"] = lut_name
    except KeyError:
        pass
    return intensity


def slant_range_time_to_ground_range(
    azimuth_time: xr.DataArray,
    slant_range_time: xr.DataArray,
    coordinate_conversion: xr.Dataset,
) -> xr.DataArray:
    """Convert slant range time to ground range using the coordinate conversion metadata.

    :param azimuth_time: azimuth time coordinates
    :param slant_range_time: slant range time
    :param coordinate_conversion: coordinate conversion dataset.
    The coordinate conversion dataset can be opened using the measurement sub-groub `coordinate_conversion`
    """
    slant_range = SPEED_OF_LIGHT / 2.0 * slant_range_time
    sr0 = coordinate_conversion.sr0.interp(azimuth_time=azimuth_time)
    srgrCoefficients = coordinate_conversion.srgrCoefficients.interp(
        azimuth_time=azimuth_time,
    )
    x = slant_range - sr0
    ground_range = (srgrCoefficients * x**srgrCoefficients.degree).sum("degree")
    return ground_range  # type: ignore


def ground_range_to_slant_range_time(
    azimuth_time: xr.DataArray,
    ground_range: xr.DataArray,
    coordinate_conversion: xr.Dataset,
) -> xr.DataArray:
    """Convert ground range to slant range time using the coordinate conversion metadata.

    :param azimuth_time: azimuth time coordinates
    :param ground_range: slant range time
    :param coordinate_conversion: coordinate conversion dataset.
    The coordinate conversion dataset can be opened using the measurement sub-groub `coordinate_conversion`
    """
    assert (coordinate_conversion.gr0 == 0.0).all()
    grsrCoefficients = coordinate_conversion.grsrCoefficients.interp(
        azimuth_time=azimuth_time,
    )
    x = ground_range
    slant_range = (grsrCoefficients * x**grsrCoefficients.degree).sum("degree")
    return 2 / SPEED_OF_LIGHT * slant_range  # type: ignore


METADATA_OPENERS = {
    "orbit": open_orbit_dataset,
    "attitude": open_attitude_dataset,
    "azimuth_fm_rate": open_azimuth_fm_rate_dataset,
    "dc_estimate": open_dc_estimate_dataset,
    "gcp": open_gcp_dataset,
    "coordinate_conversion": open_coordinate_conversion_dataset,
    "calibration": open_calibration_dataset,
    "noise_range": open_noise_range_dataset,
    "noise_azimuth": open_noise_azimuth_dataset,
}


def do_override_product_files(
    template: str, product_files: Dict[str, Tuple[str, str, str, str, str]]
) -> Dict[str, Tuple[str, str, str, str, str]]:
    overridden_product_files = {}
    for path, description in product_files.items():
        type, prefix, swath, polarization, date = description
        ext = os.path.splitext(path)[1]
        dirname = os.path.dirname(path)
        overridden_path = template.format(**locals())
        overridden_product_files[overridden_path] = description
    return overridden_product_files


def open_sentinel1_dataset(
    product_urlpath: esa_safe.PathType,
    *,
    drop_variables: Optional[Tuple[str]] = None,
    group: Optional[str] = None,
    fs: Optional[fsspec.AbstractFileSystem] = None,
    storage_options: Optional[Dict[str, Any]] = None,
    check_files_exist: bool = False,
    override_product_files: Optional[str] = None,
    parse_geospatial_attrs: bool = True,
) -> xr.Dataset:
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")

    fs, manifest_path = get_fs_path(product_urlpath, fs, storage_options)
    product_path = os.path.dirname(manifest_path)

    with fs.open(manifest_path) as file:
        common_attrs, product_files = esa_safe.parse_manifest_sentinel1(file)

    if override_product_files:
        product_files = do_override_product_files(override_product_files, product_files)

    groups = find_available_groups(
        product_files, product_path, check_files_exist=check_files_exist, fs=fs
    )

    group, burst_index = normalise_group(group)
    absgroup = f"/{group}"
    if group != "" and group not in groups:
        raise ValueError(
            f"Invalid group {group!r}, please select one of the following groups:"
            f"\n{list(groups.keys())}"
        )

    metadata = ""

    ds = xr.Dataset(attrs=common_attrs)
    gcp = None
    if group == "":
        subgroups = list(groups)
    else:
        subgroups = [
            g[len(group) + 1 :] for g in groups if g.startswith(group) and g != group
        ]

        if group.count("/") == 1:
            with fs.open(groups[group][1]) as annotation:
                if parse_geospatial_attrs:
                    gcp = open_gcp_dataset(annotation, attrs=common_attrs)

                ds = open_pol_dataset(
                    groups[group][0],
                    annotation,
                    fs=fs,
                    attrs=common_attrs,
                    gcp=gcp,
                )
        elif group.count("/") == 2:
            _, _, metadata = group.split("/", 2)
            with fs.open(groups[group][0]) as file:
                ds = METADATA_OPENERS[metadata](file, attrs=common_attrs)

    ds.attrs["group"] = absgroup
    if len(subgroups):
        ds.attrs["subgroups"] = subgroups

    if group.count("/") == 1 and burst_index is not None:
        ds = crop_burst_dataset(ds, burst_index=burst_index, gcp=gcp)

    conventions.update_attributes(ds, group=metadata)

    return ds
