import datetime
import io
import os
import re
import warnings
from collections.abc import Callable
from typing import Any

import fsspec
import xarray as xr

from . import conventions, eopf_metadata, eopf_sentinel1, esa_safe, sentinel1

POLARIZATION_INDEPENDENT_GROUPS = {"conditions/attitude", "conditions/orbit"}
SAFE_NAME_RE = re.compile(
    r"S(?P<sat>\d)(?P<platform>\w)_(?P<mode>\w{2})_(?P<product_type>\w{3})\w"
    r"_\w{4}_(?P<start>\d{8}T\d{6})_(?P<stop>\d{8}T\d{6})_(?P<orbit>\d{6})"
    r"_(?P<datatake_id>\w{6})_(?P<unique_id>\w{4})(?:_COG)?"
)
SAFE_TIME_FORMAT = "%Y%m%dT%H%M%S"
UNKNOWN_UNIQUE_ID = "UNKN"


def make_product_name(safe_name: str, common_attrs: dict[str, Any]) -> str:
    """Return the EOPF product name.

    The values come from the manifest, the SAFE name is parsed to warn about an
    inconsistent or unparsable name. The unique id and the duration come from the SAFE
    name, as the manifest has no unique id and a microsecond precision duration.
    """
    match = SAFE_NAME_RE.fullmatch(safe_name)
    name_values: dict[str, str] = {}
    if match is None:
        warnings.warn(f"cannot parse SAFE name {safe_name!r}, using the manifest")
    else:
        name_values = match.groupdict()

    start_time = datetime.datetime.fromisoformat(common_attrs["start_time"])
    stop_time = datetime.datetime.fromisoformat(common_attrs["stop_time"])
    # the SAFE name times are truncated to seconds
    start_time = start_time.replace(microsecond=0)
    stop_time = stop_time.replace(microsecond=0)
    start = start_time.strftime(SAFE_TIME_FORMAT)
    stop = stop_time.strftime(SAFE_TIME_FORMAT)
    if name_values:
        # the duration of the SAFE name takes precedence, as in the CPM
        name_start_time = datetime.datetime.strptime(
            name_values["start"], SAFE_TIME_FORMAT
        )
        name_stop_time = datetime.datetime.strptime(
            name_values["stop"], SAFE_TIME_FORMAT
        )
        duration = (name_stop_time - name_start_time).seconds
    else:
        duration = (stop_time - start_time).seconds
    # not the relative orbit, see quirk 5 in docs/DATATREE.md
    cycle = (common_attrs["orbit_number"] - 73) // 175 + 1
    sat = common_attrs["family_name"].removeprefix("SENTINEL-")
    # the SAFE name uses the beam, e.g. S3, instead of SM
    mode = common_attrs["mode"]
    if mode == "SM":
        mode = common_attrs["swaths"][0]
    platform = common_attrs["number"]
    product_type = common_attrs["product_type"]
    datatake_id = f"{int(common_attrs['mission_data_take_id']):06X}"
    values = {
        "sat": sat,
        "platform": platform,
        "mode": mode,
        "product_type": product_type,
        "start": start,
        "stop": stop,
        "orbit": f"{common_attrs['orbit_number']:06d}",
        "datatake_id": datatake_id,
    }

    differences = {}
    for field, value in values.items():
        name_value = name_values.get(field)
        if name_value is not None and name_value != value:
            differences[field] = (name_value, value)
    if differences:
        warnings.warn(
            f"SAFE name {safe_name!r} differs from the manifest, using the manifest:"
            f" {differences}"
        )

    unique_id = name_values.get("unique_id")
    if unique_id is None:
        warnings.warn(
            f"no unique id in SAFE name {safe_name!r}, using {UNKNOWN_UNIQUE_ID!r}"
        )
        unique_id = UNKNOWN_UNIQUE_ID

    product_name = (
        f"S0{sat}S{mode}{product_type}"
        f"_{start}_{duration:04}_{platform}{cycle:03}_{unique_id}_{datatake_id}"
    )
    return product_name


QUALITY_GROUPS: dict[
    str, tuple[str, str, Callable[[dict[str, Any], dict[str, Any]], xr.Dataset]]
] = {
    "quality/calibration": (
        "calibration",
        "calibration",
        eopf_sentinel1.open_calibration,
    ),
    "quality/noise_azimuth": (
        "noise_azimuth",
        "noise",
        eopf_sentinel1.open_noise_azimuth,
    ),
    "quality/noise_range": ("noise_range", "noise", eopf_sentinel1.open_noise_range),
}
ANNOTATION_GROUPS: dict[str, Callable[[dict[str, Any]], xr.Dataset | None]] = {
    "conditions/antenna_pattern": eopf_sentinel1.open_antenna_pattern,
    "conditions/attitude": eopf_sentinel1.open_attitude,
    "conditions/coordinate_conversion": eopf_sentinel1.open_coordinate_conversion,
    "conditions/doppler_centroid": eopf_sentinel1.open_doppler_centroid,
    "conditions/gcp": eopf_sentinel1.open_gcp,
    "conditions/orbit": eopf_sentinel1.open_orbit,
}


def split_measurements(
    pol_dataset: xr.Dataset, name: str
) -> dict[str | None, xr.Dataset]:
    bursts: dict[str | None, xr.Dataset] = {}
    if "number_of_bursts" in pol_dataset.attrs:
        for burst_index in range(pol_dataset.attrs["number_of_bursts"]):
            burst = sentinel1.crop_burst_dataset(pol_dataset, burst_index=burst_index)
            bursts[str(burst.attrs.get("burst_id", burst_index))] = burst
        azimuth_chunk = -1
    else:
        bursts[None] = pol_dataset
        azimuth_chunk = 4096
    measurements = {}
    for burst_id, burst in bursts.items():
        measurement = burst.measurement.rename(name)
        measurement.attrs = {"long_name": measurement.attrs["long_name"]}
        # the CPM chunks, whole TOPS bursts along azimuth
        chunks = {"azimuth_time": azimuth_chunk, measurement.dims[1]: 4096}
        measurements[burst_id] = measurement.chunk(chunks).to_dataset()
    return measurements


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
    rasterio_chunks: dict[str, int] | None = None,
) -> xr.DataTree:
    """Open a SAFE product as an experimental EOPF-layout DataTree."""
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

    safe_name, _ = os.path.splitext(os.path.basename(product_path))
    product_name = make_product_name(safe_name, common_attrs)
    root_stac_discovery = eopf_metadata.build_stac_discovery(product_name, manifest)
    title = eopf_metadata.make_product_type(
        common_attrs["mode"], common_attrs["product_type"]
    )
    dt = xr.DataTree()
    for swath, pols in swath_pols.items():
        bursts: dict[str | None, dict[str, xr.Dataset]] = {}
        pol_datasets: dict[str, dict[str, xr.Dataset]] = {}
        annotations = {}
        for pol in pols:
            measurement_path, annotation_path = groups[f"{swath}/{pol}"][:2]
            annotations[pol] = esa_safe.parse_xml(xml_files[annotation_path])
            pol_dataset = sentinel1.open_pol_dataset(
                measurement_path,
                xml_files[annotation_path],
                fs=fs,
                rasterio_chunks=rasterio_chunks,
            )
            pol_dataset = conventions.update_attributes(pol_dataset)
            measurement_name = common_attrs["product_type"].lower()
            for burst_id, burst in split_measurements(
                pol_dataset, measurement_name
            ).items():
                bursts.setdefault(burst_id, {})[pol] = burst
            for eopf_group, (
                group,
                schema_type,
                open_quality,
            ) in QUALITY_GROUPS.items():
                if f"{swath}/{pol}/{group}" in groups:
                    xml_path = groups[f"{swath}/{pol}/{group}"][0]
                    xml_dict = esa_safe.parse_xml(xml_files[xml_path], schema_type)
                    quality = open_quality(xml_dict, annotations[pol])
                    pol_datasets.setdefault(eopf_group, {})[pol] = quality
            for eopf_group, converter in ANNOTATION_GROUPS.items():
                converted = converter(annotations[pol])
                if converted is not None:
                    pol_datasets.setdefault(eopf_group, {})[pol] = converted

        annotation = annotations[pols[0]]
        burst_list = esa_safe.get_tag(annotation, "swathTiming/burstList")
        has_burst_ids = "burstId" in burst_list.get("burst", [{}])[0]
        gcp = pol_datasets["conditions/gcp"][pols[0]]
        node_groups = {}
        for eopf_group, datasets in pol_datasets.items():
            if eopf_group in POLARIZATION_INDEPENDENT_GROUPS:
                node_groups[eopf_group] = next(iter(datasets.values()))
            else:
                node_groups[eopf_group] = stack_polarizations(datasets)

        for burst_index, (burst_id, burst_pols) in enumerate(bursts.items()):
            node = product_name
            if burst_id is not None:
                node += f"_{swath}_{burst_id}"
            measurement = burst_pols[pols[0]][measurement_name]
            azimuth_time, range_coordinate = (measurement[d] for d in measurement.dims)
            footprint = sentinel1.get_footprint_linestring(
                azimuth_time, range_coordinate, gcp
            )
            relative_burst = int(burst_id) if has_burst_ids and burst_id else None
            stac_discovery = eopf_metadata.build_stac_discovery(
                node, manifest, annotation, footprint, relative_burst
            )
            node_burst_index = None if burst_id is None else burst_index
            other_metadata = {}
            for pol in pols:
                other_metadata[pol] = eopf_metadata.build_other_metadata(
                    annotations[pol], title, node_burst_index
                )
            dt[node] = xr.Dataset(
                attrs={
                    "other_metadata": other_metadata,
                    "stac_discovery": stac_discovery,
                }
            )
            dt[f"{node}/measurements"] = stack_polarizations(burst_pols)
            for eopf_group, ds in node_groups.items():
                dt[f"{node}/{eopf_group}"] = ds

    dt.attrs = {
        "other_metadata": {"eopf_category": "eocontainer", "title": title},
        "stac_discovery": root_stac_discovery,
    }
    return dt
