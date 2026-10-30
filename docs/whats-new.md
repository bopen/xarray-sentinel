# What's new

## v0.9.7 (unreleased)

- Add the experimental EOPF DataTree: `xr.open_datatree(..., engine="sentinel-1")` and
  `xr.open_groups` open a SAFE product with the layout of the ESA EOPF CPM 3.0 products.
  WV products are not supported yet.
- Add the `xarray-sentinel` command line: `convert` writes the EOPF DataTree of a SAFE
  product to Zarr and `info` prints its STAC metadata, reading only the manifest.
- Support the CDSE GRD COG products in the EOPF DataTree, reading them in whole tiles.
- Read the measurements without the global rasterio lock, so dask reads them in parallel.
- Add the `slant_range_to_ground_range` function.
- Use the `ground_range` dimension instead of `slant_range_time` in the GRD `gcp` group
  and add the `azimuth_time_gcp` and `slant_range_time_gcp` variables to all `gcp` groups.
- Accept `ground_range` in `get_footprint_linestring` for GRD products and round the
  footprint coordinates to 6 decimals.
- Add the `swath` dimension to `noise_azimuth` and keep all the noise vectors instead of
  only the first one, with their first and last lines and samples.
- Store the `attitude` variables and the `dc_estimate` polynomials as `float32`.
- Add the `fine_dce_azimuth_start_time` and `fine_dce_azimuth_stop_time` variables to
  `dc_estimate`.
- Fix `data_dc_rms_error_above_threshold` in `dc_estimate`: it is now the boolean flag
  instead of a copy of `data_dc_rms_error`.
- Raise an error when opening the groups of WV products, that returned a single vignette
  out of the many of a swath. The root group can still be opened.
- Fix `reformat.to_group_zarr` for SLC products.
- Let xarray choose the `azimuth_time` units when writing the measurements, instead of
  forcing microseconds.
- Remove the alpha `parse_eopf_metadata` option and `sentinel1.make_sentinel1_stac_item`.
- Drop support for Python 3.10: only Python >= 3.11 is supported.
- Add `typer` and `zarr` to the required dependencies and raise the minimum `dask` to
  2024.6.
