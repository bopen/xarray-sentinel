from typing import Any

import numpy as np
import xarray as xr

from . import esa_safe

GCP_VARIABLES = {
    "latitude": "latitude",
    "longitude": "longitude",
    "height": "height",
    "incidence_angle": "incidenceAngle",
    "elevation_angle": "elevationAngle",
    "azimuth_time_gcp": "azimuthTime",
    "slant_range_time_gcp": "slantRangeTime",
}


def open_antenna_pattern(annotation: dict[str, Any]) -> xr.Dataset:
    patterns = esa_safe.get_tag(
        annotation, "antennaPattern/antennaPatternList/antennaPattern"
    )
    pattern_datasets = []
    for pattern in patterns:
        slant_range_time = np.fromstring(pattern["slantRangeTime"]["$"], sep=" ")
        elevation_angle = np.fromstring(
            pattern["elevationAngle"]["$"], dtype=np.float32, sep=" "
        )
        incidence_angle = np.fromstring(
            pattern["incidenceAngle"]["$"], dtype=np.float32, sep=" "
        )
        data_vars = {
            "slant_range_time_ap": ("count", slant_range_time),
            "elevation_angle": ("count", elevation_angle),
            "incidence_angle": ("count", incidence_angle),
            "swath": pattern["swath"],
            "roll": pattern["roll"],
            "terrain_height": pattern["terrainHeight"],
        }
        coords = {"count": np.arange(slant_range_time.size)}
        pattern_dataset = xr.Dataset(data_vars=data_vars, coords=coords)
        azimuth_time = [np.datetime64(pattern["azimuthTime"], "ns")]
        pattern_datasets.append(pattern_dataset.expand_dims(azimuth_time=azimuth_time))
    return xr.concat(pattern_datasets, dim="azimuth_time", join="outer")


def open_gcp(annotation: dict[str, Any]) -> xr.Dataset:
    points = esa_safe.get_tag(
        annotation, "geolocationGrid/geolocationGridPointList/geolocationGridPoint"
    )
    lines = sorted({point["line"] for point in points})
    pixels = sorted({point["pixel"] for point in points})
    shape = (len(lines), len(pixels))
    grids = {name: np.full(shape, np.nan) for name in GCP_VARIABLES}
    grids["azimuth_time_gcp"] = np.full(shape, np.datetime64("NaT", "ns"))
    for point in points:
        index = lines.index(point["line"]), pixels.index(point["pixel"])
        for name, tag in GCP_VARIABLES.items():
            grids[name][index] = point[tag]
    # the annotated times of the first column and row, see quirk 1 in docs/DATATREE.md
    coords = {
        "azimuth_time": grids["azimuth_time_gcp"][:, 0],
        "slant_range_time": grids["slant_range_time_gcp"][0],
        "line": ("azimuth_time", lines),
        "pixel": ("slant_range_time", pixels),
    }
    dims = ("azimuth_time", "slant_range_time")
    data_vars = {name: (dims, grid) for name, grid in grids.items()}
    return xr.Dataset(data_vars=data_vars, coords=coords)


def open_coordinate_conversion(annotation: dict[str, Any]) -> xr.Dataset | None:
    coordinate_conversion_list = esa_safe.get_tag(
        annotation, "coordinateConversion/coordinateConversionList"
    )
    if "coordinateConversion" not in coordinate_conversion_list:
        return None
    conversions = coordinate_conversion_list["coordinateConversion"]
    srgr_coefficients = [
        np.fromstring(conversion["srgrCoefficients"]["$"], sep=" ")
        for conversion in conversions
    ]
    grsr_coefficients = [
        np.fromstring(conversion["grsrCoefficients"]["$"], sep=" ")
        for conversion in conversions
    ]
    data_vars = {
        "gr0": ("azimuth_time", [c["gr0"] for c in conversions]),
        "sr0": ("azimuth_time", [c["sr0"] for c in conversions]),
        "slant_range_time": (
            "azimuth_time",
            [c["slantRangeTime"] for c in conversions],
        ),
        "srgr_coefficients": (("azimuth_time", "degree"), srgr_coefficients),
        "grsr_coefficients": (("azimuth_time", "degree"), grsr_coefficients),
    }
    coords = {
        "azimuth_time": [np.datetime64(c["azimuthTime"], "ns") for c in conversions],
        "degree": np.arange(srgr_coefficients[0].size),
    }
    return xr.Dataset(data_vars=data_vars, coords=coords)
