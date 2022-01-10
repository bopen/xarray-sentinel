# xarray-sentinel

Easily explore and access the SAR data products of the
[Copernicus Sentinel-1 satellite mission](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1)
in Python.

This Open Source project is sponsored by B-Open - https://www.bopen.eu.

## Features

- supports the following data products as [distributed by ESA](https://scihub.copernicus.eu/dhus/#/home):
  - Sentinel-1 Single Look Complex (SLC):
    - Stripmap (SM) - *alpha*
    - Interferometric Wide Swath (IW) - *alpha*
    - Extra Wide Swath (EW) - *alpha*
    - Wave (WV) - *technology preview*
  - Sentinel-1 Ground Range Detected (GRD) SM/IW/EW/WV - *technology preview*
- creates ready-to-use [Xarray](https://xarray.pydata.org) `Dataset`s that map the data
  lazily and efficiently in terms of both memory usage and disk / network access - *alpha*
- reads all SAR imagery data: GRD images, SLC swaths and SLC bursts - *alpha*
- reads several metadata elements:
  satellite orbit and attitude, ground control points, radiometric calibration look up tables,
  Doppler centroid estimation and more - *alpha*
- reads uncompressed and compressed SAFE data products on the local computer or
  on a network via [*fsspec*](https://filesystem-spec.readthedocs.io) - *technology preview*
- allows larger-than-memory and distributed processing via [*dask*](https://dask.org) - *alpha*

Overall the software is in the **alpha** phase and the usual caveats apply.
A few features, identified as *technology preview* above, are not fully usable yet.

## Install

The easiest way to install *xarray-sentinel* is in a *conda* environment.
You may create a new environment, activate it, install the package and its dependencies
with the following commands:

```shell
    conda create -n XARRAY-SENTINEL
    conda activate XARRAY-SENTINEL
    conda install -c conda-forge fsspec rioxarray xarray xmlschema
    pip install xarray-sentinel
```

## Usage

The SAR data products of the Copernicus Sentinel-1 satellite mission are distributed in
the SAFE format, composed of a few raster data files in TIFF and several metadata files in XML.
The aim of *xarray-sentinel* is to provide a developer-friendly Python interface to all data and
several metadata elements as Xarray `Dataset`s in order to enable easy processing of SAR data
into value-added products.

Due to the inherent complexity and redundancy of the SAFE format *xarray-sentinel*
maps it to a tree of *groups* where every *group* may be opened as a `Dataset`,
but it may also contain *subgroups*, that are listed in the `"subgroups"` attribute.

### Open the root dataset

For example let's explore the Sentinel-1 SLC Stripmap product in the local folder
`./S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE`.
First we can open the SAR data product by passing the `engine="sentinel-1"` to `xr.open_dataset`
and we can access the root group of the product, also known as `/`:

```python-repl
>>> import xarray as xr
>>> slc_sm_path = "./S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
>>> xr.open_dataset(slc_sm_path, engine="sentinel-1")
<xarray.Dataset>
Dimensions:  ()
Data variables:
    *empty*
Attributes: ...
    constellation:              sentinel-1
    platform:                   sentinel-1a
    instrument:                 ['c-sar']
    sat:orbit_state:            ascending
    sat:absolute_orbit:         37258
    sat:relative_orbit:         86
    ...                         ...
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['S3']
    group:                      /
    subgroups:                  ['S3', 'S3/VH', 'S3/VH/gcp', 'S3/VH/orbit', '...
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-...

```

The root `Dataset` does not contain any data variable, but only attributes that provides general information
on the product and a description of the tree structure of the data.
The attribute `group` contains the name of the current group and the `subgroups` attribute shows
the names of all available groups below this one.

### Open the measurements datasets

In order to open the other groups we need to add the keyword `group` to `xr.open_dataset`.
So we can read the measurement by selecting the desired bean mode and the polarization,
in this example the data contains the S3 beam mode and we select the VH polarization with `group="S3/VH"`:

```python-repl
>>> xr.open_dataset(slc_sm_path, group="S3/VH", engine="sentinel-1")
<xarray.Dataset>
Dimensions:           (slant_range_time: 18998, azimuth_time: 36895)
Coordinates:
    pixel             (slant_range_time) int64 ...
    line              (azimuth_time) int64 ...
  * slant_range_time  (slant_range_time) float64 ...
  * azimuth_time      (azimuth_time) datetime64[ns] ...
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    sar:center_frequency:       5.40500045433435
    constellation:              sentinel-1
    platform:                   sentinel-1a
    instrument:                 ['c-sar']
    sat:orbit_state:            ascending
    sat:absolute_orbit:         37258
    ...                         ...
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['S3']
    group:                      /S3/VH
    subgroups:                  ['gcp', 'orbit', 'attitude', 'dc_estimate', '...
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-...

```

The `measurement` variable contains the Single Look Complex measurements as a `complex64`
and it has dimensions `slant_range_time` and `azimuth_time`.
The `azimuth_time` is a time coordinates that contains the zero-Dopper UTC time associated with the image line
and `slant_range_time` is a `np.float64` coordinate that contains the two-ways range time associated with
image the pixel.

### Open the metadata datasets

The measurement group contains several subgroups with metadata associated to the image, at the moment
*xarray-sentinel* supports the following metadata datasets:

- `gcp` from the `<geolocationGridPoint>` tags in the annotation XML
- `orbit` from the `<orbit>` tags in the annotation XML
- `attitude` from the `<attitude>` tags in the annotation XML
- `cd_estimate` from the `<dcEstimate>` tags in the annotation XML
- `azimuth_fm_rate` from the `<azimuthFmRate>` tags in the annotation XML
- `calibration` from the `<calibrationVector>` tags in the calibration XML

For example the image calibration metadata associated with the `S3/VH` image can be read using
`group="S3/VH/calibration"`:

```python-repl
>>> xr.open_dataset(slc_sm_path, group="S3/VH/calibration", engine="sentinel-1")
<xarray.Dataset>
Dimensions:       (line: 22, pixel: 476)
Coordinates:
  * line          (line) int64 0 1925 3850 5775 7700 ... 34649 36574 38499 40424
  * pixel         (pixel) int64 0 40 80 120 160 ... 18880 18920 18960 18997
Data variables:
    azimuth_time  (line) datetime64[ns] ...
    sigmaNought   (line, pixel) float64 ...
    betaNought    (line, pixel) float64 ...
    gamma         (line, pixel) float64 ...
    dn            (line, pixel) float64 ...
Attributes: ...
    constellation:              sentinel-1
    platform:                   sentinel-1a
    instrument:                 ['c-sar']
    sat:orbit_state:            ascending
    sat:absolute_orbit:         37258
    sat:relative_orbit:         86
    ...                         ...
    xs:instrument_mode_swaths:  ['S3']
    group:                      /S3/VH/calibration
    Conventions:                CF-1.8
    title:                      Calibration coefficients
    comment:                    The dataset contains calibration information ...
    history:                    created by xarray_sentinel-...

```

Note that in this case the dimensions are `line` and `pixel` with coordinates corresponding to
the sub-grid of the original image where it is defined the calibration Look Up Table.

The groups present in a typical Sentinel-1 SLC Stripmap product are:

```
/
└─ S3
   ├─ VH
   │  ├─ gcp
   │  ├─ orbit
   │  ├─ attitude
   │  ├─ dc_estimate
   │  ├─ azimuth_fm_rate
   │  └─ calibration
   └─ VV
      ├─ gcp
      ├─ orbit
      ├─ attitude
      ├─ dc_estimate
      ├─ azimuth_fm_rate
      └─ calibration

```

## Advanced usage

Products representing the TOPS acquisition modes, IW and EW, are more complex because they contain
several beam modes in the same SAFE package, but also because the measurement array is a collage
of sub-images called *bursts*.

*xarray-sentinel* provides a helper function that crops a burst out of a measurement dataset for you.

You need to first open the desired measurement dataset, for example the VH polarisation
of the first IW swath of the `S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4`
product in the current folder:

```python-repl
>>> slc_iw_path = "./S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
>>> slc_iw1_vh = xr.open_dataset(slc_iw_path, group="IW1/VH", engine="sentinel-1")
>>> slc_iw1_vh
<xarray.Dataset>
Dimensions:           (pixel: 21632, line: 13509)
Coordinates:
  * pixel             (pixel) int64 0 1 2 3 4 ... 21627 21628 21629 21630 21631
  * line              (line) int64 0 1 2 3 4 5 ... 13504 13505 13506 13507 13508
    slant_range_time  (pixel) float64 ...
    azimuth_time      (line) datetime64[ns] ...
Data variables:
    measurement       (line, pixel) complex64 ...
Attributes: (12/20)
    sar:center_frequency:       5.40500045433435
    azimuth_steering_rate:      1.590368784
    number_of_bursts:           9
    lines_per_burst:            1501
    constellation:              sentinel-1
    platform:                   sentinel-1b
    ...                         ...
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VH
    subgroups:                  ['gcp', 'orbit', 'attitude', 'dc_estimate', '...
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-...

```

Note that the measurement data for IW and EW acquisition modes can not be indexed by physical
coordinates because of the collage nature of the image.

Now the 9th burst out of 9 can be cropped from the swath data using `burst_index=8`, via:

```python-repl
>>> import xarray_sentinel
>>> xarray_sentinel.crop_burst_dataset(slc_iw1_vh, burst_index=8)
<xarray.Dataset>
Dimensions:           (slant_range_time: 21632, azimuth_time: 1501)
Coordinates:
    pixel             (slant_range_time) int64 0 1 2 3 ... 21629 21630 21631
    line              (azimuth_time) int64 12008 12009 12010 ... 13507 13508
  * slant_range_time  (slant_range_time) float64 0.005343 0.005343 ... 0.005679
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:46.27227...
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: (12/22)
    sar:center_frequency:       5.40500045433435
    azimuth_steering_rate:      1.590368784
    number_of_bursts:           9
    lines_per_burst:            1501
    constellation:              sentinel-1
    platform:                   sentinel-1b
    ...                         ...
    group:                      /IW1/VH
    subgroups:                  ['gcp', 'orbit', 'attitude', 'dc_estimate', '...
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-0.1.2.dev189+gf816...
    azimuth_anx_time:           2210.634453
    burst_index:                8

```

Note that the helper function also performs additional changes like swapping the dimenstions
to the physical coordinates and adding burst attributes.

As a quick way to access burst data you can add the `burst_index` to the group specification on
open, for example `group="IW1/VH/8"`.
The burst groups are not listed in the `subgroup` attribute because they are not structural.

```python-repl
>>> xr.open_dataset(slc_iw_path, group="IW1/VH/8", engine="sentinel-1")
<xarray.Dataset>
Dimensions:           (slant_range_time: 21632, azimuth_time: 1501)
Coordinates:
    pixel             (slant_range_time) int64 ...
    line              (azimuth_time) int64 ...
  * slant_range_time  (slant_range_time) float64 0.005343 0.005343 ... 0.005679
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:46.27227...
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: (12/22)
    sar:center_frequency:       5.40500045433435
    azimuth_steering_rate:      1.590368784
    number_of_bursts:           9
    lines_per_burst:            1501
    constellation:              sentinel-1
    platform:                   sentinel-1b
    ...                         ...
    group:                      /IW1/VH
    subgroups:                  ['gcp', 'orbit', 'attitude', 'dc_estimate', '...
    azimuth_anx_time:           2210.634453
    burst_index:                8
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-0.1.2.dev189+gf816...

```

## Project badges

[![on-push](https://github.com/bopen/xarray-sentinel/actions/workflows/on-push.yml/badge.svg)](https://github.com/bopen/xarray-sentinel/actions/workflows/on-push.yml)
[![codecov](https://codecov.io/gh/bopen/xarray-sentinel/branch/main/graph/badge.svg?token=OLw9it0i18)](https://codecov.io/gh/bopen/xarray-sentinel)

## Contributing

The main repository is hosted on GitHub,
testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/bopen/xarray-sentinel

Lead developers:

- [Aureliana Barghini](https://github.com/aurghs) - [B-Open](https://www.bopen.eu)
- [Alessandro Amici](https://github.com/alexamici) - [B-Open](https://www.bopen.eu)

Main contributors:

- [Corrado Avolio](https://github.com/corrado9999) - [e-GEOS](https://www.e-geos.it)

See also the list of [contributors](https://github.com/bopen/xarray-sentinel/contributors) who participated in this project.

## License

```
Copyright 2021-2022, B-Open Solutions srl and the xarray-sentinel authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
