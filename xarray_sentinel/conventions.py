import typing as T

import xarray as xr

VARIABLE_ATTRIBUTES: T.Dict[str, T.Dict[str, str]] = {
    "q0": {"units": "1"},
    "q1": {"units": "1"},
    "q2": {"units": "1"},
    "pitch": {"units": "degrees"},
    "roll": {"units": "degrees"},
    "yaw": {"units": "degrees"},
    "time": {},
    "x": {"units": "m", "long_name": "position_x"},
    "y": {"units": "m", "long_name": "position_y"},
    "z": {"units": "m", "long_name": "position_z"},
    "vx": {"units": "m s-1", "long_name": "velocity_x"},
    "vy": {"units": "m s-1", "long_name": "velocity_y"},
    "vz": {"units": "m s-1", "long_name": "velocity_z"},
}


def update_attributes(ds: xr.Dataset) -> xr.Dataset:
    for var in ds.variables:
        attrs = VARIABLE_ATTRIBUTES.get(str(var), {})
        ds.variables[var].attrs.update(attrs)  # type: ignore
    return ds
