import datetime
import io
import os
import pathlib
import re
from collections.abc import Callable
from typing import Any

import fsspec
import xarray as xr

from . import conventions, eopf_metadata, eopf_sentinel1, esa_safe, sentinel1

EOPF_GROUPS: dict[str, tuple[str, Callable[..., xr.Dataset]]] = {
    "conditions/attitude": ("attitude", sentinel1.open_attitude_dataset),
    "conditions/doppler_centroid": ("dc_estimate", sentinel1.open_dc_estimate_dataset),
    "conditions/gcp": ("gcp", sentinel1.open_gcp_dataset),
    "conditions/orbit": ("orbit", sentinel1.open_orbit_dataset),
    "quality/calibration": ("calibration", sentinel1.open_calibration_dataset),
    "quality/noise_azimuth": ("noise_azimuth", sentinel1.open_noise_azimuth_dataset),
    "quality/noise_range": ("noise_range", sentinel1.open_noise_range_dataset),
}
POLARIZATION_INDEPENDENT_GROUPS = {"conditions/attitude", "conditions/orbit"}
SAFE_NAME_RE = re.compile(
    r"S(\d)(\w)_(\w{2})_(\w{3})\w_\w{4}_(\w{15})_(\w{15})_(\d{6})_(\w{6})_(\w{4})"
)
SAFE_TIME_FORMAT = "%Y%m%dT%H%M%S"


def make_product_name(safe_name: str) -> str:
    match = SAFE_NAME_RE.fullmatch(safe_name)
    if match is None:
        raise ValueError(f"cannot parse SAFE name {safe_name!r}")
    sat, platform, mode, product_type, start, stop, orbit, datatake_id, unique_id = (
        match.groups()
    )
    start_time = datetime.datetime.strptime(start, SAFE_TIME_FORMAT)
    stop_time = datetime.datetime.strptime(stop, SAFE_TIME_FORMAT)
    duration = (stop_time - start_time).seconds
    # not the relative orbit, see quirk 5 in docs/DATATREE.md
    cycle = (int(orbit) - 73) // 175 + 1
    product_name = (
        f"S0{sat}S{mode}{product_type}_{start}_{duration:04}_{platform}{cycle:03}"
        f"_{unique_id}_{datatake_id}"
    )
    return product_name


ANNOTATION_GROUPS: dict[str, Callable[[dict[str, Any]], xr.Dataset | None]] = {
    "conditions/antenna_pattern": eopf_sentinel1.open_antenna_pattern,
    "conditions/coordinate_conversion": eopf_sentinel1.open_coordinate_conversion,
}


def split_bursts(pol_dataset: xr.Dataset) -> dict[str | None, xr.Dataset]:
    if "number_of_bursts" not in pol_dataset.attrs:
        return {None: pol_dataset}
    bursts: dict[str | None, xr.Dataset] = {}
    for burst_index in range(pol_dataset.attrs["number_of_bursts"]):
        burst = sentinel1.crop_burst_dataset(pol_dataset, burst_index=burst_index)
        bursts[str(burst.attrs.get("burst_id", burst_index))] = burst
    return bursts


def stack_polarizations(datasets: dict[str, xr.Dataset]) -> xr.Dataset:
    stacked = xr.concat(list(datasets.values()), dim="polarization", join="outer")
    return stacked.assign_coords(polarization=list(datasets))


def open_datatree(
    product_urlpath: esa_safe.PathType,
    *,
    fs: fsspec.AbstractFileSystem | None = None,
    storage_options: dict[str, Any] | None = None,
    check_files_exist: bool = False,
    override_product_files: str | None = None,
    **kwargs: Any,
) -> xr.DataTree:
    fs, manifest_path = sentinel1.get_fs_path(product_urlpath, fs, storage_options)
    product_path = os.path.dirname(manifest_path)
    manifest = io.BytesIO(fs.cat_file(manifest_path))

    common_attrs, product_files = esa_safe.parse_manifest_sentinel1(manifest)
    if override_product_files:
        product_files = sentinel1.do_override_product_files(
            override_product_files, product_files
        )
    groups = sentinel1.find_available_groups(
        product_files,
        product_path,
        common_attrs["product_type"],
        check_files_exist=check_files_exist,
        fs=fs,
    )
    xml_files = {
        path: io.BytesIO(fs.cat_file(path))
        for paths in groups.values()
        for path in paths
        if path.endswith(".xml")
    }

    swath_pols: dict[str, list[str]] = {}
    for group in groups:
        if group.count("/") == 1:
            swath, _, pol = group.partition("/")
            swath_pols.setdefault(swath, []).append(pol)

    product_name = make_product_name(pathlib.PurePosixPath(product_path).stem)
    dt = xr.DataTree()
    for swath, pols in swath_pols.items():
        bursts: dict[str | None, dict[str, xr.Dataset]] = {}
        pol_datasets: dict[str, dict[str, xr.Dataset]] = {}
        annotations = {}
        other_metadata = {}
        for pol in pols:
            measurement_path, annotation_path = groups[f"{swath}/{pol}"][:2]
            annotations[pol] = esa_safe.parse_xml(xml_files[annotation_path])
            pol_dataset = sentinel1.open_pol_dataset(
                measurement_path, xml_files[annotation_path], fs=fs
            )
            pol_dataset = conventions.update_attributes(pol_dataset)
            for burst_id, burst in split_bursts(pol_dataset).items():
                burst = burst.rename(measurement="slc").drop_attrs(deep=False)
                bursts.setdefault(burst_id, {})[pol] = burst
            for eopf_group, (group, opener) in EOPF_GROUPS.items():
                if f"{swath}/{pol}/{group}" in groups:
                    xml_path = groups[f"{swath}/{pol}/{group}"][0]
                    ds = conventions.update_attributes(opener(xml_files[xml_path]))
                    pol_datasets.setdefault(eopf_group, {})[pol] = ds.drop_attrs(
                        deep=False
                    )
            for eopf_group, converter in ANNOTATION_GROUPS.items():
                converted = converter(annotations[pol])
                if converted is not None:
                    pol_datasets.setdefault(eopf_group, {})[pol] = converted
            other_metadata[pol] = eopf_metadata.build_other_metadata(annotations[pol])

        stac_discovery = eopf_metadata.build_stac_discovery(
            "noid", manifest, annotations[pols[0]]
        )
        node_groups = {}
        for eopf_group, datasets in pol_datasets.items():
            if eopf_group in POLARIZATION_INDEPENDENT_GROUPS:
                node_groups[eopf_group] = next(iter(datasets.values()))
            else:
                node_groups[eopf_group] = stack_polarizations(datasets)

        for burst_id, burst_pols in bursts.items():
            node = product_name
            if burst_id is not None:
                node += f"_{swath}_{burst_id}"
            dt[node] = xr.Dataset(
                attrs={
                    "other_metadata": other_metadata,
                    "stac_discovery": stac_discovery,
                }
            )
            dt[f"{node}/measurements"] = stack_polarizations(burst_pols)
            for eopf_group, ds in node_groups.items():
                dt[f"{node}/{eopf_group}"] = ds

    return dt
