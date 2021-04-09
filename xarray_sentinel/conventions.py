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
    "x": {"units": "m"},
    "y": {"units": "m"},
    "z": {"units": "m"},
    "vx": {"units": "m s-1"},
    "vy": {"units": "m s-1"},
    "vz": {"units": "m s-1"},
}


def update_attributes(ds: xr.Dataset) -> xr.Dataset:
    for var in ds.variables:
        attrs = VARIABLE_ATTRIBUTES.get(str(var), {})
        ds.variables[var].attrs.update(attrs)  # type: ignore
    return ds
