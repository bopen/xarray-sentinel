# What's new

## v0.9.7 (2026-10-23)

- New **experimental** EOPF DataTree layout:
  `xr.open_datatree(..., engine="sentinel-1")`, also available via `xr.open_groups`;
  WV is not supported yet.
- New `xarray-sentinel` CLI: `convert` writes the experimental EOPF DataTree of a SAFE
  product to Zarr and `info` prints its product level STAC metadata.
- Python 3.11 or newer is required.
- `noise_azimuth` now has a `swath` dimension and holds every block; GRD `gcp` uses
  `ground_range`.
- The alpha `parse_eopf_metadata` option and `sentinel1.make_sentinel1_stac_item` are gone.
- Fix `dc_estimate.data_dc_rms_error_above_threshold` and SLC Zarr conversion.
