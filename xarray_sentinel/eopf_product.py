import io
import os
import pathlib
from collections.abc import Callable
from typing import Any

import fsspec
import xarray as xr

from . import conventions, eopf_metadata, esa_safe, sentinel1

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

    product_name = pathlib.PurePosixPath(product_path).stem
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
            other_metadata[pol] = eopf_metadata.build_other_metadata(annotations[pol])

        stac_discovery = sentinel1.make_sentinel1_stac_item(
            "noid", manifest, annotations[pols[0]]
        )
        node_groups = {}
        for eopf_group, datasets in pol_datasets.items():
            if eopf_group in POLARIZATION_INDEPENDENT_GROUPS:
                node_groups[eopf_group] = next(iter(datasets.values()))
            else:
                node_groups[eopf_group] = stack_polarizations(datasets)

        for burst_id, burst_pols in bursts.items():
            node = f"{product_name}_{swath}"
            if burst_id is not None:
                node += f"_{burst_id}"
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
