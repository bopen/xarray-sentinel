# Sentinel-1 SAFE as an EOPF DataTree

Goal: open a Sentinel-1 L1 SAFE product as an `xr.DataTree` with the layout of the
ESA EOPF Zarr products.

```python
dt = xr.open_datatree("S1A_IW_SLC__1SDV_....SAFE", engine="sentinel-1")
```

## Decisions

- Target layout: EOPF CPM 3.0.
- Names, structure and dimensions follow EOPF exactly, values stay physically correct
  where EOPF is wrong, see [EOPF quirks](#eopf-quirks). The quirks are candidates for
  CPM bug reports.
- Entry point: `Sentinel1Backend.open_datatree` and `open_groups_as_dict`.
- Strict EOPF content: no groups that EOPF lacks, for now. See `azimuth_fm_rate` in
  [Open points](#open-points).

## References

- CPM 3.0: the `eopf` 3.0.0 wheel on PyPI.
  - SAFE to EOPF mapping: `eopf/store/mapping/S01S{IW,EW,SM,WV}{SLC,GRD}_pv1.0.0_mv1.0.0.json`
  - reshaping: `eopf/store/product_specific/S01.py`, `S01GRHSafeFinalize` and
    `S01SXWSLCSafeFinalize`
  - node names: `eopf/store/mapping_manager.py`
- CPM 3.0 sample: `S1C_IW_SLC__1SDV_20260731T234807_20260731T234821_008794_0116E8_C079`
  in the `sentinel-1-l1-slc-zarr3` collection of https://stac.core.eopf.eodc.eu
- CPM 2.7 samples, the previous layout: collections `sentinel-1-l1-slc` and
  `sentinel-1-l1-grd` of the same STAC.

## Target layout

IW SLC: one node per swath and burst, 27 nodes for 3 swaths of 9 bursts, polarisations
stacked along `polarization`. Leaves list data variables only.

```
/                                   attrs: stac_discovery, other_metadata
└─ S01SIWSLC_20260731T234807_0014_C050_C079_0116E8_IW3_258176
   │                                attrs: stac_discovery, other_metadata, processing_history
   ├─ measurements
   │  └─ slc (polarization, azimuth_time, slant_range_time) complex64
   ├─ conditions
   │  ├─ antenna_pattern
   │  │  ├─ slant_range_time_ap, elevation_angle, incidence_angle (polarization, azimuth_time, count)
   │  │  └─ swath, roll, terrain_height (polarization, azimuth_time)
   │  ├─ attitude
   │  │  └─ q0, q1, q2, q3, wx, wy, wz, roll, pitch, yaw (azimuth_time)
   │  ├─ doppler_centroid
   │  │  ├─ data_dc_polynomial, geometry_dc_polynomial (polarization, azimuth_time, degree)
   │  │  └─ t0, data_dc_rms_error, data_dc_rms_error_above_threshold,
   │  │     fine_dce_azimuth_start_time, fine_dce_azimuth_stop_time (polarization, azimuth_time)
   │  ├─ gcp
   │  │  └─ latitude, longitude, height, incidence_angle, elevation_angle,
   │  │     azimuth_time_gcp, slant_range_time_gcp (polarization, azimuth_time, slant_range_time)
   │  └─ orbit
   │     └─ position, velocity (azimuth_time, axis)    axis = "x", "y", "z"
   └─ quality
      ├─ calibration
      │  └─ sigma_nought, beta_nought, gamma, dn (polarization, azimuth_time, slant_range_time)
      ├─ noise_range
      │  └─ noise_range_lut (polarization, azimuth_time, slant_range_time)
      └─ noise_azimuth
         ├─ noise_azimuth_lut (polarization, azimuth_time, swath)
         └─ first_azimuth_line, last_azimuth_line,
            first_range_sample, last_range_sample (polarization, swath)
```

Other product types, from the CPM code and not yet checked on samples:

- EW SLC: as IW with swaths `EW1` to `EW5`.
- SM SLC: one node, the measurement is not split.
- WV SLC: one node per vignette.
- GRD: one node, range dimension `ground_range`, measurement `grd` uint16, plus
  `conditions/coordinate_conversion`.

Chunks, from the CPM mapping: TOPS SLC `{azimuth_time: whole burst, slant_range_time: 4096}`,
other types 4096 x 4096.

### Node names

```
S0{sat}S{mode}{type}_{start}_{duration:04}_{platform}{N:03}_{unique_id}_{datatake_id}[_{swath}_{burst_id}]
```

All fields come from the SAFE name, except `burst_id` from `swathTiming` and
`N = (absolute_orbit - 73) // 175 + 1`, see quirk 5. WV appends `_{WVn}_{image_number}`.

| SAFE | EOPF CPM 3.0 node |
|---|---|
| `S1C_IW_SLC__1SDV_20260731T234807_20260731T234821_008794_0116E8_C079` | `S01SIWSLC_20260731T234807_0014_C050_C079_0116E8_IW3_258176` |
| `S1C_IW_SLC__1SDH_20260531T194042_20260531T194109_007902_01011D_EC26` | `S01SIWSLC_20260531T194042_0027_C045_EC26_01011D_IW1_64850` |
| `S1C_IW_GRDH_1SDV_20261017T111256_20261017T111323_009924_013C8F_ECF5` | `S01SIWGRD_20261017T111256_0027_C057_ECF5_013C8F` |

### Attributes

- root
  - `stac_discovery`: STAC item from `manifest.safe`, one asset per node.
  - `other_metadata`: `{"eopf_category": "eocontainer", "title": "S01SIWSLC"}`.
- node
  - `stac_discovery`: manifest and annotation properties, `sar:relative_burst`, burst
    footprint as `geometry`, `detectionPerformed`, `thermalNoiseCorrectionPerformed`.
  - `processing_history`: from the manifest `safe:processing`.
  - `other_metadata`: keyed by polarisation, each with `eopf_category: "eoproduct"`,
    `title`, `image_number`, `quality_information`, `general_annotation`,
    `image_annotation` and `burst_timing`. `burst_timing` holds the node's burst entry of
    `swathTiming`, including the per-line `first_valid_sample` and `last_valid_sample`.

### Previous layout: CPM 2.7

Still served by the sample service: one node per polarisation, swath and burst, named
`..._{POL}_{swath}_{burst_id}`, with `line` and `pixel` coordinates, a
`conditions/burst_info` group and `swath_timing` instead of `burst_timing`, in Zarr v2.

## Differences from xarray-sentinel

| xarray-sentinel `group=` | EOPF | Differences |
|---|---|---|
| `IW1/VV`, `IW1/VV/<n>` | `measurements/slc`, `grd` | one node per burst instead of the swath image and burst crop, `measurement` is `slc` or `grd`, no `line`/`pixel`, product attrs move to the node |
| `IW1/VV/orbit` | `conditions/orbit` | `(axis, azimuth_time)` is `(azimuth_time, axis)`, `axis` is `"x", "y", "z"` |
| `IW1/VV/attitude` | `conditions/attitude` | `q0` to `q3` are float32 |
| `IW1/VV/dc_estimate` | `conditions/doppler_centroid` | adds `fine_dce_azimuth_start_time` and `fine_dce_azimuth_stop_time` |
| `IW1/VV/gcp` | `conditions/gcp` | snake_case names, adds 2-D `azimuth_time_gcp` and `slant_range_time_gcp` |
| none, `open_antenna_pattern` is not exposed | `conditions/antenna_pattern` | `(azimuth_time, count)` with 2-D `slant_range_time_ap`, adds `swath` |
| `IW/VV/coordinate_conversion`, GRD only | `conditions/coordinate_conversion` | snake_case names |
| `IW1/VV/azimuth_fm_rate` | none | only in `other_metadata` |
| `IW1/VV/calibration` | `quality/calibration` | snake_case names, `(line, pixel)` is `(azimuth_time, slant_range_time\|ground_range)` |
| `IW1/VV/noise_range` | `quality/noise_range` | as calibration |
| `IW1/VV/noise_azimuth` | `quality/noise_azimuth` | snake_case names, `(swath, line)` is `(polarization, azimuth_time, swath)` |
| none | `burst_timing` attrs | per-line valid samples |

Replica, reference replica and terrain height are only in `other_metadata` in EOPF.

## EOPF quirks

What we do in each case follows the decisions above.

1. GCP `azimuth_time` is linear in `line` between the first and last product line times
   and ignores burst timing. In IW SLC it is up to ~300 ms (~2 km) away from the
   annotated GCP times. We use the annotated time of the first GCP column, as
   `open_gcp_dataset` does.
1. Doppler centroid `degree` is labelled `[2, 1, 0]` while the coefficients are in XML
   order d0, d1, d2, so `(c * x**c.degree).sum("degree")` is wrong. We label `[0, 1, 2]`.
1. `fine_dce_azimuth_start_time` and `fine_dce_azimuth_stop_time` are bool, with the
   `long_name` of `data_dc_rms_error_above_threshold`. We store datetimes.
1. TOPS burst `azimuth_time` spans `lines_per_burst * azimuth_time_interval` over
   `lines_per_burst` points: the last line is one interval (~2 ms) late, times are
   encoded in µs. We use `start + k * azimuth_time_interval` in ns, as
   `crop_burst_dataset` does.
1. The name token `N` applies the S1A relative orbit formula to all platforms: S1C
   absolute orbit 7902 gives `045`, `sat:relative_orbit` is 31. It is an identifier, so
   we reproduce it.
1. `noise_azimuth`, from reading the code, not checked on data: times come from the
   linear grid of quirk 1, all swath columns share the `azimuth_time` of the last swath
   (GRD has several), blocks of a swath are concatenated keeping the first and last
   line and sample of the first block only.
1. Wrong `long_name`s, e.g. `doppler_centroid/azimuth_time` "of terrain height
   measurement" and `noise_range/line` "image pixel".

## Open points

- `line` and `pixel` coordinates: CPM 2.7 has them, the CPM 3.0 sample does not. The
  CPM 3.0 code drops them from calibration and noise but builds them for gcp. Check on a
  CPM 3.0 conversion, step 11, until then omit them.
- `azimuth_fm_rate`, needed by sarsen: in EOPF it is only
  `other_metadata[pol]["general_annotation"]["azimuth_fm_rate_list"]`.
- `zarr_conventions`, `spatial:bbox` and `proj:code` on the CPM 3.0 sample come from the
  sample service GeoZarr post-processing: out of scope.
- `calibrate_amplitude` and `calibrate_intensity` interpolate on `line` and `pixel`, they
  need a variant for the EOPF layout.
- The manifest is still read with ElementTree, so `eopf_metadata.build_stac_discovery`
  takes it as a path or file while the annotation is a dict from `esa_safe.parse_xml`.
  `parse_xml(..., "manifest")` with `strip_namespaces=True` decodes all the test
  products in ~4 ms with plain keys, lists for repeated fields except `frameSet/frame`
  (a list for WV only), ints for `missionDataTakeID` and orbit numbers as
  `[{"@type": "start", "$": ...}, ...]`. But `my-xfdu.xsd` was generated automatically
  long ago and is untested, so this is on hold.

## Plan

One PR with tests per step. Step 1 comes first, steps 2 to 9 are independent and each
adds converters to the step 1 registry, steps 10 and 11 come last.

1. Skeleton and test harness. Rewrite `eopf_product.open_datatree` around a context per
   swath and polarisation that parses the manifest and each XML once and opens each
   measurement once. Build each group with a registry `{eopf_path: converter}`, one
   node per swath and burst, stacking the per-polarisation results along
   `polarization` except orbit and attitude. Move `parse_eopf_metadata` out of
   `open_sentinel1_dataset`. Add a helper comparing node paths, variable names, dims
   and dtypes, with fixtures of the CPM 3.0 sample structure.
1. Node names: a function tested on the examples above.
1. orbit, attitude, doppler_centroid: from the existing openers, quirks 2 and 3.
1. gcp: snake_case names, 2-D annotated times, quirk 1.
1. calibration, noise_range: snake_case names, range coordinate from `pixel` as
   `image_slant_range_time + pixel / range_sampling_rate` for SLC and
   `pixel * range_pixel_spacing` for GRD.
1. noise_azimuth: from the existing opener, quirk 6.
1. antenna_pattern, and GRD coordinate_conversion.
1. measurements: split TOPS SLC by burst with `crop_burst_dataset` on one lazy array per
   swath and polarisation, quirk 4. Rename to `slc` or `grd`, keep only `long_name`,
   set the CPM chunks. SM and GRD as one image, WV per vignette.
1. Attributes, in three parts:
   1. `stac_discovery` of root and nodes following the CPM mapping keys
      `stac_discovery`, `stac_discovery_annotation` and
      `stac_discovery_annotation_manifest`, extending `eopf_metadata.build_stac_discovery`.
   1. `other_metadata` extending `eopf_metadata.build_other_metadata`: `burst_timing`
      with the node's burst merged in, drop empty `swath_merging` and the CPM
      `DEPRECATED_ATTRS`, numeric lists instead of `$` strings, `t_0` as `t0`.
   1. `processing_history`.
1. API and docs: `Sentinel1Backend.open_datatree` and `open_groups_as_dict`, README,
   this file.
1. Validation: convert one or two full SAFE products with CPM 3.0 in a throwaway
   environment (the test SAFEs lack the `support/*.xsd` the CPM needs), compare
   structure exactly and values within tolerance, list the deviations due to the
   quirks. Optionally open our Zarr output with `xarray-eopf`.
