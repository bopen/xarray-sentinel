# What's new

## v0.9.8 (unreleased)

Fewer required dependencies: opening the products needs neither `scipy` nor `zarr`.

### New features

- Add the `s3` extra to read the products from S3 object stores.
- Run the tests on Windows and macOS as well as on Linux in the CI: they are tested
  platforms.

### Breaking changes

- Move `scipy` to the new `scipy` extra. `calibrate_amplitude` and
  `calibrate_intensity` with a non constant calibration LUT, as `sigmaNought` and
  `gamma`, and the slant / ground range conversions need it and raise an `ImportError`
  without it. Opening the products and calibrating with the usually constant
  `betaNought` do not need it.
- Move `zarr` and `numcodecs` to the new `zarr` extra, needed by the `to-eopf-zarr`
  command: `uvx 'xarray-sentinel[zarr]' to-eopf-zarr ...`.
- Remove the `lab` extra: `pip install "xarray-sentinel[lab]"` no longer works, use
  `make lab` from a source checkout.
- Replace `typer` with `click`, already required by `dask` and `rasterio`, for the
  `xarray-sentinel` command: the commands and their arguments are the same, the help
  and the errors are plain text.

### Bug fixes

- Join the paths inside a product with `/` on Windows too: opening zipped products
  failed with a `FileNotFoundError`, as did products on other non local file systems.

## v0.9.7 (2026-11-04)

The first release with the EOPF DataTree, in beta, the `xarray-sentinel` command line
and a lot of performance improvements.

### New features

- Open a SAFE product as an EOPF `DataTree` with
  `xr.open_datatree(..., engine="sentinel-1")`. The layout is the one written by the EOPF
  CPM 3.0, see [DATATREE.md](DATATREE.md). WV products are not supported yet.
- Carry the product level `stac_discovery` and `other_metadata` attributes on the root,
  and `stac_discovery`, `other_metadata` and `processing_history` on every product node,
  with an `xarray-sentinel` entry in the processing history.
- Convert a SAFE product to EOPF Zarr and print its STAC metadata with the new
  `xarray-sentinel` command: `to-eopf-zarr` writes the Zarr store, `info` prints the
  product level STAC item.
- Add the `slant_range_to_ground_range` function.
- Store the GRD measurements in the EOPF Zarr as `uint16` with the CPM chunks.

### Performance

- Read the measurements without the global rasterio lock, so dask reads them in
  parallel.
- Fetch each XML file once when opening the EOPF DataTree.
- Read only the manifest to print the STAC metadata with `info`.

### Breaking changes

- Drop support for Python 3.10: only Python >= 3.11 is supported.
- The `noise_azimuth` group gains a `swath` dimension and holds all the vectors, where
  it kept only the first one, on `line`.
- The `gcp` group of the GRD products has a `ground_range` dimension instead of
  `slant_range_time`.
- Opening a non-root group of a WV product raises a `ValueError`, where it returned a
  single vignette out of the many of a swath. The root group can still be opened.
- `to_zarr` writes the `azimuth_time` coordinates with the units chosen by xarray,
  usually `nanoseconds`, instead of forcing `microseconds`.
- Add `typer` and `zarr` to the required dependencies and raise the minimum `dask` to
  2024.6.

### Bug fixes

- `data_dc_rms_error_above_threshold` in `dc_estimate` held a copy of
  `data_dc_rms_error`; it is now the boolean flag from the annotation.

### Documentation

- Add [DATATREE.md](DATATREE.md) with the EOPF layout and the deliberate differences
  from EOPF, and rewrite CONTRIBUTING.md for uv.
