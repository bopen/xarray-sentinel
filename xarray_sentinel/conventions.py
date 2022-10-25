"""CF representation of metadata according to Sentinel-1 Product Specification.

See: S1-RS-MDA-52-7441, DI-MPC-PB, MPC-0240, 3/7, 27/02/2020
https://sentinel.esa.int/documents/247904/1877131/Sentinel-1-Product-Specification
"""

import xarray as xr

from . import __version__

GROUP_ATTRIBUTES = {
    "orbit": {
        "title": "Orbit information used by the IPF during processing",
        "comment": (
            "The dataset contains a sets of orbit state vectors that are updated along azimuth."
            " The values represent the interpolated values used by the IPF"
            " and are derived from the sub-commutated ancillary data from the ISPs"
            " or from an input auxiliary orbit file"
        ),
    },
    "attitude": {
        "title": "Attitude information used by the IPF during processing",
        "comment": (
            "The dataset contains a sets of attitude data records that are updated along azimuth."
            " The values represent the interpolated values used by the IPF"
            " and are derived from the sub-commutated ancillary data from the ISPs"
            " or from an input auxiliary orbit file"
        ),
    },
    "gcp": {
        "title": "Geolocation grid",
        "comment": (
            "The dataset contains geolocation grid point entries for each line/pixel"
            " combination based on a configured resolution."
            " The list contains an entry for each update made along azimuth"
        ),
    },
    "calibration": {
        "title": "Calibration coefficients",
        "comment": (
            "The dataset contains calibration information and the beta nought, sigma nought,"
            " gamma and digital number (DN) Look-up Tables (LUT) that can be used for"
            " absolute product calibration"
        ),
    },
}

VARIABLE_ATTRIBUTES = {
    "line": {"units": "1", "long_name": "product line number"},
    "pixel": {"units": "1", "long_name": "product pixel number"},
    "azimuth_time": {"long_name": "zero-Doppler azimuth time", "standard_name": "time"},
    # NOTE: `slant_range_time` is not expressed as `np.timedelta64[ns]` in order to keep enough
    #   accuracy for interferometric processing, i.e. c * 1ns / 2 ~= 15cm.
    "slant_range_time": {"units": "s", "long_name": "slant range time / two-way delay"},
    "ground_range": {"units": "m", "long_name": "ground range"},
    "axis": {"units": "1", "long_name": "coordinate index"},
    "degree": {"units": "1", "long_name": "polynomial degree"},
    "latitude": {"units": "degrees_north", "long_name": "geodetic latitude"},
    "longitude": {"units": "degrees_east", "long_name": "geodetic longitude"},
    "height": {"units": "m", "long_name": "height above sea level"},
    "incidenceAngle": {"units": "°", "long_name": "incidence angle"},
    "elevationAngle": {"units": "°", "long_name": "elevation angle"},
    "q0": {"units": "1", "long_name": "Q0 attitude quaternion"},
    "q1": {"units": "1", "long_name": "Q1 attitude quaternion"},
    "q2": {"units": "1", "long_name": "Q2 attitude quaternion"},
    "q3": {"units": "1", "long_name": "Q3 attitude quaternion"},
    "roll": {"units": "°", "long_name": "platform roll"},
    "pitch": {"units": "°", "long_name": "platform pitch"},
    "yaw": {"units": "°", "long_name": "platform yaw"},
    "wx": {"units": "° s-1", "long_name": "X component of angular velocity vector"},
    "wy": {"units": "° s-1", "long_name": "Y component of angular velocity vector"},
    "wz": {"units": "° s-1", "long_name": "Z component of angular velocity vector"},
    "position": {"units": "m", "long_name": "ECEF position"},
    "velocity": {"units": "m s-1", "long_name": "ECEF velocity"},
    "sigmaNought": {"units": "m m-1", "long_name": "sigma nought calibration LUT"},
    "betaNought": {"units": "m m-1", "long_name": "beta nought calibration LUT"},
    "gamma": {"units": "m m-1", "long_name": "gamma calibration LUT"},
    "dn": {"units": "1", "long_name": "original digital number calibration LUT"},
    "noiseRangeLut": {"units": "1", "long_name": "range thermal noise correction LUT"},
    "noiseAzimuthLut": {
        "units": "1",
        "long_name": "azimuth thermal noise correction LUT",
    },
    "gr0": {
        "units": "m",
        "long_name": "ground range origin for slant range calculation",
    },
    "grsrCoefficients": {
        "units": "1",
        "long_name": "polynomial to convert from ground range to slant range",
    },
    "sr0": {
        "units": "m",
        "long_name": "slant range origin for ground range calculation",
    },
    "srgrCoefficients": {
        "units": "1",
        "long_name": "polynomial to convert from slant range to ground range",
    },
    "t0": {
        "units": "s",
        "long_name": "Two-way slant range time origin",
    },
    "data_dc_polynomial": {
        "units": "1",
        "long_name": "Coppler centroid estimated from data",
    },
    "azimuth_fm_rate_polynomial": {
        "units": "1",
        "long_name": "Azimuth FM rate coefficient array",
    },
    "measurement": {"units": "1", "long_name": "digital number"},
}


def update_attributes(ds: xr.Dataset, group: str = "") -> xr.Dataset:
    # NOTE: keep the version in sync with the capabilities of CF compliance checkers
    ds.attrs["Conventions"] = "CF-1.8"
    ds.attrs.update(GROUP_ATTRIBUTES.get(group, {}))
    ds.attrs["history"] = f"created by xarray_sentinel-{__version__}"
    for var in ds.variables:
        attrs = VARIABLE_ATTRIBUTES.get(str(var), {})
        ds.variables[var].attrs.update(attrs)
    return ds
