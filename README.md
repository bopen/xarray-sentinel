# xarray-sentinel

Easily explore and access the SAR data products of the
[Copernicus Sentinel-1 satellite mission](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1)
in Python.

This Open Source project is sponsored by B-Open - https://www.bopen.eu

## Features

- creates ready-to-use [Xarray](https://xarray.pydata.org) `Dataset`'s that map the data
  lazily and efficiently in terms of both memory usage and disk / network access - *alpha*
- reads all SAR imagery data: GRD images, SLC swaths and SLC bursts - *alpha*
- reads several metadata elements:
  satellite orbit and attitude, ground control points, radiometric calibration look up tables,
  Doppler centroid estimation and more - *alpha*
- supports the following data products as [distributed by ESA](https://scihub.copernicus.eu/dhus/#/home):
  - Sentinel-1 Single Look Complex (SLC):
    - Stripmap (SM) - *alpha*
    - Interferometric Wide Swath (IW) - *alpha*
    - Extra Wide Swath (EW) - *alpha*
    - Wave (WV) - *technology preview*
  - Sentinel-1 Ground Range Detected (GRD) SM/IW/EW/WV - *technology preview*
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
several metadata elements as Xarray `Dataset`'s in order to enable easy processing of SAR data
into value-added products.

Due to the inherent complexity and redundancy of the SAFE format *xarray-sentinel*
maps it to a tree of *groups* where every *group* may be opened as a `Dataset`,
but it may also contain *subgroups*, that are listed in the `"subgroups"` attribute.

For example let's explore the Sentinel-1 SLC Stripmap product in the local folder
`./S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE`.
First we can open the SAR data product by passing the `engine="sentinel-1"` to `xr.open_dataset`
and we can access the root group of the product, also known as `/`:

```python-repl
>>> import xarray as xr
>>> slc_iw_path = "./S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
>>> xr.open_dataset(slc_iw_path, engine="sentinel-1")
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
The attribute `group` contain the name of the current group and the `subgroups` attribute shows
the names of all available groups below this one.

In order to open the other groups we need to add the keyword `group` to `xr.open_dataset`, so
read the measurement of the VH polarization of first IW swath we will use `group="S3/VH"`:

```python-repl
>>> xr.open_dataset(slc_iw_path, group="S3/VH", engine="sentinel-1")
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

For example, the groups present in a typical Sentinel-1 SLC Stripmap product are:

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

## Sentinel-1 SLC IW

### Data

Currently, xarray-sentinel provides access as Xarray datasets to the following data:

- full image
- individual swaths
- individual SLC bursts
- gcp
- orbit
- attitude
- calibration
- dc_estimate
- azimuth_fm_rate

using `azimuth_time` and `slant_range_time` dimensions when it make sense.

## Examples:

### Open the gcp dataset

To load the gcp relative to the VV polarisation of first swath use the key `group="IW1/VV/gcp"`:

```python-repl
>>> xr.open_dataset(slc_iw_path, group="IW1/VV/gcp", engine="sentinel-1")
<xarray.Dataset>
Dimensions:           (azimuth_time: 10, slant_range_time: 21)
Coordinates:
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:24.20973...
  * slant_range_time  (slant_range_time) float64 0.005343 0.00536 ... 0.005679
    line              (azimuth_time) int64 0 1501 3002 ... 10507 12008 13508
    pixel             (slant_range_time) int64 0 1082 2164 ... 19476 20558 21631
Data variables:
    latitude          (azimuth_time, slant_range_time) float64 ...
    longitude         (azimuth_time, slant_range_time) float64 ...
    height            (azimuth_time, slant_range_time) float64 ...
    incidenceAngle    (azimuth_time, slant_range_time) float64 ...
    elevationAngle    (azimuth_time, slant_range_time) float64 ...
Attributes: ...
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VV/gcp
    Conventions:                CF-1.8
    title:                      Geolocation grid
    comment:                    The dataset contains geolocation grid point e...
    history:                    created by xarray_sentinel-...

```

### Open the orbit dataset

Similarly for orbit data use `group="IW1/VV/attitude"`:

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/VV/orbit")
<xarray.Dataset>
Dimensions:       (axis: 3, azimuth_time: 17)
Coordinates:
  * azimuth_time  (azimuth_time) datetime64[ns] 2021-04-01T05:25:19 ... 2021-...
  * axis          (axis) int64 0 1 2
Data variables:
    position      (axis, azimuth_time) ...
    velocity      (axis, azimuth_time) ...
Attributes: ...
    reference_system:           Earth Fixed
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    ...                         ...
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VV/orbit
    Conventions:                CF-1.8
    title:                      Orbit information used by the IPF during proc...
    comment:                    The dataset contains a sets of orbit state ve...
    history:                    created by xarray_sentinel-...

```

### Attitude and calibration datasets

For attitude data use `group="IW1/VV/attitude"`:

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/VV/attitude")
<xarray.Dataset>
Dimensions:       (azimuth_time: 25)
Coordinates:
  * azimuth_time  (azimuth_time) datetime64[ns] 2021-04-01T05:26:24.750001 .....
Data variables:
    q0            (azimuth_time) float64 ...
    q1            (azimuth_time) float64 ...
    q2            (azimuth_time) float64 ...
    q3            (azimuth_time) float64 ...
    wx            (azimuth_time) float64 ...
    wy            (azimuth_time) float64 ...
    wz            (azimuth_time) float64 ...
    pitch         (azimuth_time) float64 ...
    roll          (azimuth_time) float64 ...
    yaw           (azimuth_time) float64 ...
Attributes: ...
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VV/attitude
    Conventions:                CF-1.8
    title:                      Attitude information used by the IPF during p...
    comment:                    The dataset contains a sets of attitude data ...
    history:                    created by xarray_sentinel-...

```

and for calibration data use `group="IW1/VV/calibration"`:

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/VV/calibration")
<xarray.Dataset>
Dimensions:       (line: 30, pixel: 542)
Coordinates:
  * line          (line) int64 -1042 -556 91 577 ... 13042 13688 14175 14661
  * pixel         (pixel) int64 0 40 80 120 160 ... 21520 21560 21600 21631
Data variables:
    azimuth_time  (line) datetime64[ns] ...
    sigmaNought   (line, pixel) float64 ...
    betaNought    (line, pixel) float64 ...
    gamma         (line, pixel) float64 ...
    dn            (line, pixel) float64 ...
Attributes: ...
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VV/calibration
    Conventions:                CF-1.8
    title:                      Calibration coefficients
    comment:                    The dataset contains calibration information ...
    history:                    created by xarray_sentinel-...

```

### Open a single swath / polarisation dataset

### Crop single SLC burst dataset

A single burst can be cropped out of the swath data. *xarray_sentinel* offer an helper function
that also performs additional changes like swapping the dimenstions:

```python-repl
>>> sentinel1.crop_burst_dataset(swath_polarisation_ds, burst_index=8)
<xarray.Dataset>
Dimensions:           (slant_range_time: 21632, azimuth_time: 1501)
Coordinates:
    pixel             (slant_range_time) int64 0 1 2 3 ... 21629 21630 21631
    line              (azimuth_time) int64 12008 12009 12010 ... 13507 13508
  * slant_range_time  (slant_range_time) float64 0.005343 0.005343 ... 0.005679
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:46.27227...
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    azimuth_steering_rate:      1.590368784
    sar:center_frequency:       5.40500045433435
    number_of_bursts:           9
    lines_per_burst:            1501
    constellation:              sentinel-1
    platform:                   sentinel-1b
    ...                         ...
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    group:                      /IW1/VV
    subgroups:                  ['gcp', 'orbit', 'attitude', 'dc_estimate', '...
    Conventions:                CF-1.8
    history:                    created by xarray_sentinel-...
    burst_index:                8

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
Copyright 2021, B-Open Solutions srl and the xarray-sentinel authors.

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
