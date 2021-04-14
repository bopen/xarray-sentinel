import os
import typing as T
import warnings

import numpy as np
import xarray as xr

from xarray_sentinel import conventions, esa_safe


def open_gcp_dataset(product_path: T.Union[str, "os.PathLike[str]"]) -> xr.Dataset:
    geolocation_grid_points = esa_safe.parse_geolocation_grid_points(product_path)
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


def open_attitude_dataset(product_path: T.Union[str, "os.PathLike[str]"]) -> xr.Dataset:
    attitude = esa_safe.parse_attitude(product_path)
    shape = len(attitude)
    variables = ["q0", "q1", "q2", "wx", "wy", "wz", "pitch", "roll", "yaw", "time"]
    data_vars: T.Dict[str, T.List[T.Any]] = {var: ("time", []) for var in variables}  # type: ignore

    for k in range(shape):
        for var in variables:
            data_vars[var][1].append(attitude[k][var])

    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        attrs={"Conventions": "CF-1.7"},
    )

    ds = conventions.update_attributes(ds)
    ds = ds.update({"time": ds.time.astype(np.datetime64)})
    return ds


def open_orbit_dataset(product_path: T.Union[str, "os.PathLike[str]"]) -> xr.Dataset:
    orbit = esa_safe.parse_orbit(product_path)
    shape = len(orbit)

    reference_system = orbit[0]["frame"]
    variables = ["time", "x", "y", "z", "vx", "vy", "vz"]
    data_vars: T.Dict[str, T.List[T.Any]] = {var: ("time", []) for var in variables}  # type: ignore

    for k in range(shape):
        data_vars["time"][1].append(orbit[k]["time"])
        data_vars["x"][1].append(orbit[k]["position"]["x"])
        data_vars["y"][1].append(orbit[k]["position"]["y"])
        data_vars["z"][1].append(orbit[k]["position"]["z"])
        data_vars["vx"][1].append(orbit[k]["velocity"]["x"])
        data_vars["vy"][1].append(orbit[k]["velocity"]["y"])
        data_vars["vz"][1].append(orbit[k]["velocity"]["z"])
        if orbit[k]["frame"] != reference_system:
            warnings.warn(
                f"reference_system is not consistent in all the state vectors. "
                f"xpath: .//orbit//frame \n File: ${product_path}"
            )
            reference_system = None

    attrs = {"Conventions": "CF-1.7"}
    if reference_system is not None:
        attrs.update({"reference_system": reference_system})
    ds = xr.Dataset(
        data_vars=data_vars,  # type: ignore
        attrs=attrs,  # type: ignore
    )
    ds = conventions.update_attributes(ds)
    ds = ds.update({"time": ds.time.astype(np.datetime64)})
    return ds


OPENERS = {
    "gcp": open_gcp_dataset,
    "attitude": open_attitude_dataset,
    "orbit": open_orbit_dataset,
}