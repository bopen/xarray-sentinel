import xarray as xr

VARIABLE_ATTRIBUTES = {
    "azimuth_time": {"long_name": "azimuth time", "standard_name": "time"},
    # NOTE: `slant_range_time` is not expressed as `np.timedelta64[ns]` in order to keep enough
    #   accuracy for interferometric processing, i.e. c * 1ns / 2 ~= 15cm.
    "slant_range_time": {"units": "s", "long_name": "slant range time / two-way delay"},
    "latitude": {"units": "degrees_north"},
    "longitude": {"units": "degrees_east"},
    "height": {"units": "m"},
    "incidenceAngle": {"units": "degrees"},
    "elevationAngle": {"units": "degrees"},
    "q0": {"units": "1"},
    "q1": {"units": "1"},
    "q2": {"units": "1"},
    "q3": {"units": "1"},
    "roll": {"units": "degrees"},
    "pitch": {"units": "degrees"},
    "yaw": {"units": "degrees"},
    "time": {"standard_name": "time"},
    "x": {"units": "m", "long_name": "position x"},
    "y": {"units": "m", "long_name": "position y"},
    "z": {"units": "m", "long_name": "position z"},
    "vx": {"units": "m s-1", "long_name": "velocity x"},
    "vy": {"units": "m s-1", "long_name": "velocity y"},
    "vz": {"units": "m s-1", "long_name": "velocity z"},
}


def update_attributes(ds: xr.Dataset) -> xr.Dataset:
    ds.attrs["Conventions"] = "CF-1.7"
    for var in ds.variables:
        attrs = VARIABLE_ATTRIBUTES.get(str(var), {})
        ds.variables[var].attrs.update(attrs)  # type: ignore
    return ds
