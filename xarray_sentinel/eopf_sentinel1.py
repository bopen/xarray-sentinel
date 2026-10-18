"""Convert the Sentinel-1 SAFE XML files to the datasets of the EOPF layout.

References
----------
  - Sentinel-1 documents:
    https://sentiwiki.copernicus.eu/web/s1-documents
  - Sentinel-1 Product Specification 3/16/3 14 November 2025 S1-RS-MDA-52-7441 documenting IPF 4.00
    https://sentiwiki.copernicus.eu/__attachments/a_8ed8a4b44eb1585570c8ce755c81f47149b5710b878272ab3b40e9cfa2c9e046/S1-RS-MDA-52-7441-Sentinel-1-Product-Specification-2025-3.16.3.pdf
  - EOPF CPM 3.0, the SAFE to Zarr converter that defines the target layout, see docs/DATATREE.md
    https://pypi.org/project/eopf/3.0.0/
  - Sentinel-1 L1 and L2 Zarr product format of the EOPF S1 L12 reference processor
    https://s1.pages.eopf.copernicus.eu/s1-l12-rp/main/pfs/product_format_overview.html
"""

import warnings
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from . import esa_safe

ATTITUDE_VARIABLES = ["q0", "q1", "q2", "q3", "wx", "wy", "wz", "pitch", "roll", "yaw"]
CALIBRATION_VARIABLES = {
    "sigma_nought": "sigmaNought",
    "beta_nought": "betaNought",
    "gamma": "gamma",
    "dn": "dn",
}
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


def open_attitude(annotation: dict[str, Any]) -> xr.Dataset:
    attitudes = esa_safe.get_tag(annotation, "generalAnnotation/attitudeList/attitude")
    # all float32, not only the quaternions as in EOPF, see docs/DATATREE.md
    data_vars = {
        name: ("azimuth_time", np.array([a[name] for a in attitudes], dtype=np.float32))
        for name in ATTITUDE_VARIABLES
    }
    coords = {"azimuth_time": [np.datetime64(a["time"], "ns") for a in attitudes]}
    return xr.Dataset(data_vars=data_vars, coords=coords)


def open_orbit(annotation: dict[str, Any]) -> xr.Dataset:
    orbits = esa_safe.get_tag(annotation, "generalAnnotation/orbitList/orbit")
    reference_system = orbits[0]["frame"]
    if any(orbit["frame"] != reference_system for orbit in orbits):
        warnings.warn("reference_system is not consistent in all the state vectors. ")
    axis = ["x", "y", "z"]
    position = [[orbit["position"][a] for a in axis] for orbit in orbits]
    velocity = [[orbit["velocity"][a] for a in axis] for orbit in orbits]
    data_vars = {
        "position": (("azimuth_time", "axis"), position),
        "velocity": (("azimuth_time", "axis"), velocity),
    }
    coords = {
        "azimuth_time": [np.datetime64(orbit["time"], "ns") for orbit in orbits],
        "axis": axis,
    }
    attrs = {"reference_system": reference_system}
    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def open_doppler_centroid(annotation: dict[str, Any]) -> xr.Dataset:
    estimates = esa_safe.get_tag(
        annotation, "dopplerCentroid/dcEstimateList/dcEstimate"
    )
    data_dc_polynomial = [
        np.fromstring(e["dataDcPolynomial"]["$"], dtype=np.float32, sep=" ")
        for e in estimates
    ]
    geometry_dc_polynomial = [
        np.fromstring(e["geometryDcPolynomial"]["$"], dtype=np.float32, sep=" ")
        for e in estimates
    ]
    data_vars = {
        "t0": ("azimuth_time", [e["t0"] for e in estimates]),
        "data_dc_polynomial": (("azimuth_time", "degree"), data_dc_polynomial),
        "geometry_dc_polynomial": (("azimuth_time", "degree"), geometry_dc_polynomial),
        "data_dc_rms_error": ("azimuth_time", [e["dataDcRmsError"] for e in estimates]),
        "data_dc_rms_error_above_threshold": (
            "azimuth_time",
            [e["dataDcRmsErrorAboveThreshold"] for e in estimates],
        ),
        # times, not bool as in EOPF, see quirk 3 in docs/DATATREE.md
        "fine_dce_azimuth_start_time": (
            "azimuth_time",
            [np.datetime64(e["fineDceAzimuthStartTime"], "ns") for e in estimates],
        ),
        "fine_dce_azimuth_stop_time": (
            "azimuth_time",
            [np.datetime64(e["fineDceAzimuthStopTime"], "ns") for e in estimates],
        ),
    }
    coords = {
        "azimuth_time": [np.datetime64(e["azimuthTime"], "ns") for e in estimates],
        # the polynomial powers, not reversed as in EOPF, see quirk 2 in docs/DATATREE.md
        "degree": np.arange(data_dc_polynomial[0].size),
    }
    return xr.Dataset(data_vars=data_vars, coords=coords)


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
    range_name, range_values = range_coordinate(np.array(pixels), annotation)
    coords = {
        # the annotated times of the first column, see quirk 1 in docs/DATATREE.md
        "azimuth_time": grids["azimuth_time_gcp"][:, 0],
        range_name: range_values,
        "line": ("azimuth_time", lines),
        "pixel": (range_name, pixels),
    }
    dims = ("azimuth_time", range_name)
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


def range_coordinate(
    pixel: np.ndarray, annotation: dict[str, Any]
) -> tuple[str, np.ndarray]:
    product_information = esa_safe.get_tag(
        annotation, "generalAnnotation/productInformation"
    )
    image_information = esa_safe.get_tag(annotation, "imageAnnotation/imageInformation")
    projection = product_information["projection"]
    if projection == "Slant Range":
        name = "slant_range_time"
        start = image_information["slantRangeTime"]
        step = 1 / product_information["rangeSamplingRate"]
    elif projection == "Ground Range":
        name = "ground_range"
        start = 0.0
        step = image_information["rangePixelSpacing"]
    else:
        raise ValueError(f"unknown projection {projection!r}")
    return name, start + pixel * step


def open_range_vectors(
    vectors: list[dict[str, Any]],
    variables: dict[str, str],
    annotation: dict[str, Any],
) -> xr.Dataset:
    pixel = np.fromstring(vectors[0]["pixel"]["$"], dtype=int, sep=" ")
    for vector in vectors:
        if not np.array_equal(
            np.fromstring(vector["pixel"]["$"], dtype=int, sep=" "), pixel
        ):
            raise ValueError("Unable to organise vectors in a regular line-pixel grid")
    range_name, range_values = range_coordinate(pixel, annotation)
    dims = ("azimuth_time", range_name)
    data_vars = {
        name: (
            dims,
            [np.fromstring(v[tag]["$"], dtype=np.float32, sep=" ") for v in vectors],
        )
        for name, tag in variables.items()
    }
    coords = {
        "azimuth_time": [np.datetime64(v["azimuthTime"], "ns") for v in vectors],
        range_name: range_values,
        "line": ("azimuth_time", [v["line"] for v in vectors]),
        "pixel": (range_name, pixel),
    }
    return xr.Dataset(data_vars=data_vars, coords=coords)


def open_calibration(
    calibration: dict[str, Any], annotation: dict[str, Any]
) -> xr.Dataset:
    vectors = esa_safe.get_tag(calibration, "calibrationVectorList/calibrationVector")
    ds = open_range_vectors(vectors, CALIBRATION_VARIABLES, annotation)
    ds.attrs["absolute_calibration_constant"] = esa_safe.get_tag(
        calibration, "calibrationInformation/absoluteCalibrationConstant"
    )
    return ds


def open_noise_range(noise: dict[str, Any], annotation: dict[str, Any]) -> xr.Dataset:
    vectors = esa_safe.get_tag(noise, "noiseRangeVectorList/noiseRangeVector")
    return open_range_vectors(vectors, {"noise_range_lut": "noiseRangeLut"}, annotation)


def azimuth_time_coordinate(line: np.ndarray, annotation: dict[str, Any]) -> np.ndarray:
    image_information = esa_safe.get_tag(annotation, "imageAnnotation/imageInformation")
    swath_timing = esa_safe.get_tag(annotation, "swathTiming")
    azimuth_time: np.ndarray = pd.date_range(
        start=image_information["productFirstLineUtcTime"],
        end=image_information["productLastLineUtcTime"],
        periods=image_information["numberOfLines"],
    ).to_numpy(dtype="datetime64[ns]", copy=True)
    interval = pd.Timedelta(image_information["azimuthTimeInterval"] * 10**9, unit="ns")
    lines_per_burst = swath_timing["linesPerBurst"]
    for burst_index, burst in enumerate(swath_timing["burstList"].get("burst", [])):
        start = lines_per_burst * burst_index
        azimuth_time[start : start + lines_per_burst] = pd.date_range(
            start=burst["azimuthTime"], periods=lines_per_burst, freq=interval
        )
    return azimuth_time.take(line)


def open_noise_azimuth(noise: dict[str, Any], annotation: dict[str, Any]) -> xr.Dataset:
    vectors = esa_safe.get_tag(noise, "noiseAzimuthVectorList/noiseAzimuthVector")
    vector_datasets = []
    for vector in vectors:
        line = np.fromstring(vector["line"]["$"], dtype=int, sep=" ")
        noise_azimuth_lut = np.fromstring(
            vector["noiseAzimuthLut"]["$"], dtype=np.float32, sep=" "
        )
        data_vars = {
            "noise_azimuth_lut": ("line", noise_azimuth_lut),
            "first_azimuth_line": vector["firstAzimuthLine"],
            "last_azimuth_line": vector["lastAzimuthLine"],
            "first_range_sample": vector["firstRangeSample"],
            "last_range_sample": vector["lastRangeSample"],
        }
        vector_dataset = xr.Dataset(data_vars=data_vars, coords={"line": line})
        vector_datasets.append(vector_dataset.expand_dims(swath=[vector["swath"]]))
    # one swath entry per block on the lines of all blocks, see quirk 6 in docs/DATATREE.md
    ds = xr.concat(vector_datasets, dim="swath", join="outer")
    azimuth_time = azimuth_time_coordinate(ds.line.values, annotation)
    ds = ds.assign_coords(
        azimuth_time=("line", azimuth_time), swath=ds.swath.values.astype(str)
    )
    return ds.swap_dims(line="azimuth_time").transpose("azimuth_time", "swath")
