# xarray-sentinel

Easily access and explore the SAR data products of the
[Copernicus Sentinel-1 satellite mission](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1)
in Python.

This Open Source project is sponsored by B-Open - https://www.bopen.eu.

## Features

*xarray-sentinel* is a Python library and [*Xarray*](https://xarray.pydata.org) backend
with the following functionalities:

- supports the following data products as [distributed by ESA](https://scihub.copernicus.eu/dhus/#/home):
  - Sentinel-1 Ground Range Detected (GRD):
    - Stripmap (SM)
    - Interferometric Wide Swath (IW)
    - Extra Wide Swath (EW)
  - Sentinel-1 Single Look Complex (SLC) SM/IW/EW
- creates ready-to-use *Xarray* `Dataset`s that map the data
  lazily and efficiently in terms of both memory usage and disk / network access
- reads all SAR imagery data: GRD images, SLC swaths and SLC bursts
- reads several metadata elements:
  satellite orbit and attitude, ground control points, radiometric calibration look up tables,
  Doppler centroid estimation and more
- (partially broken, see [#127](https://github.com/bopen/xarray-sentinel/issues/127)) reads uncompressed and compressed SAFE data products on the local computer or
  on a network via [*fsspec*](https://filesystem-spec.readthedocs.io)
- supports larger-than-memory and distributed data access via [*Dask*](https://dask.org) and
  [*rioxarray*](https://corteva.github.io/rioxarray) /
  [*rasterio*](https://rasterio.readthedocs.io) / [*GDAL*](https://gdal.org)
- provides a few helpers for simple operations involving metadata like
  cropping individual bursts out of IW SLC swaths,
  applying radiometric calibration polynomials,
  converting slant to ground range for GRD products and
  computing geospatial metadata.

Overall, the software is in the **beta** phase and the usual caveats apply.

## Install

The easiest way to install *xarray-sentinel* is in a *conda* environment.
The following commands create a new environment, activate it, install the package and its dependencies:

```shell
    conda create -n XARRAY-SENTINEL
    conda activate XARRAY-SENTINEL
    conda install -c conda-forge dask "rasterio=>1.3.0" xarray-sentinel
```

## Usage

The SAR data products of the Copernicus Sentinel-1 satellite mission are distributed in
the SAFE format, composed of a few raster data files in TIFF and several metadata files in XML.
The aim of *xarray-sentinel* is to provide a developer-friendly Python interface to all data and
several metadata elements as Xarray `Dataset`s to enable easy processing of SAR data
into value-added products.

Due to the inherent complexity and redundancy of the SAFE format *xarray-sentinel*
maps it to a tree of *groups* where every *group* may be opened as a `Dataset`,
but it may also contain *subgroups*, that are listed in the `subgroups` attribute.

The following sections show some example of xarray-sentinel usage.
In the `notebooks` folder you
can also find notebooks, one for each supported product, that allow you to explore the
data in more detail using the xarray-sentinel functions.

### The root dataset

For example let's explore the Sentinel-1 SLC Stripmap product in the local folder
`./S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE`.
First, we can open the SAR data product by passing the `engine="sentinel-1"` option to `xr.open_dataset`
and access the root group of the product, also known as `/`:

```python-repl
>>> import xarray as xr
>>> slc_sm_path = "tests/data/S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
>>> xr.open_dataset(slc_sm_path, engine="sentinel-1")
<xarray.Dataset>
Dimensions:  ()
Data variables:
    *empty*
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                SM
    swaths:                              ['S3']
    orbit_number:                        37258
    relative_orbit_number:               86
    ...
    start_time:                          2021-04-01T15:28:55.111501
    stop_time:                           2021-04-01T15:29:14.277650
    group:                               /
    subgroups:                           ['S3', 'S3/VH', 'S3/VH/orbit', 'S3/V...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

The root `Dataset` does not contain any data variable, but only attributes that provide general information
on the product and a description of the tree structure of the data.
The `group` attribute contains the name of the current group and the `subgroups` attribute shows
the names of all available groups below this one.

### Measurements datasets

To open the other groups we need to add the keyword `group` to `xr.open_dataset`.
The measurement can then be read by selecting the desired beam mode and polarization.
In this example, the data contains the S3 beam mode and the VH polarization with `group="S3/VH"` is selected:

```python-repl
>>> slc_s3_vh = xr.open_dataset(slc_sm_path, group="S3/VH", engine="sentinel-1", chunks=2048)
>>> slc_s3_vh
<xarray.Dataset>
Dimensions:           (slant_range_time: 18998, azimuth_time: 36895)
Coordinates:
    pixel             (slant_range_time) int64 ...
    line              (azimuth_time) int64 ...
  * azimuth_time      (azimuth_time) datetime64[ns] ...
  * slant_range_time  (slant_range_time) float64 ...
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                SM
    swaths:                              ['S3']
    orbit_number:                        37258
    relative_orbit_number:               86
    ...
    geospatial_lon_min:                  42.772483374347
    geospatial_lon_max:                  43.75770573943618
    group:                               /S3/VH
    subgroups:                           ['orbit', 'attitude', 'azimuth_fm_ra...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

The `measurement` variable contains the Single Look Complex measurements as a `complex64`
and has dimensions `slant_range_time` and `azimuth_time`.
The `azimuth_time` is an `np.datetime64` coordinate that contains the UTC zero-Doppler time
associated with the image line
and `slant_range_time` is an `np.float64` coordinate that contains the two-way range time interval
in seconds associated with the image pixel.

Since Sentinel-1 IPF version 3.40, a unique identifier for bursts has been added to the SLC product metadata.
For these products, the list of the burst ids is stored the `burst_ids` dataset attribute.

### Metadata datasets

The measurement group contains several subgroups with metadata associated with the image. Currently,
*xarray-sentinel* supports the following metadata datasets:

- product XML file
  - `orbit` from the `<orbit>` tags
  - `attitude` from the `<attitude>` tags
  - `azimuth_fm_rate` from the `<azimuthFmRate>` tags
  - `dc_estimate` from the `<dcEstimate>` tags
  - `gcp` from the `<geolocationGridPoint>` tags
  - `coordinate_conversion` from the `<coordinateConversion>` tags
- calibration XML file
  - `calibration` from the `<calibrationVector>` tags
- noise XML file
  - `noise_range` from the `<noiseRangeVector>` tags
  - `noise_azimuth` from the `<noiseAzimuthVector>` tags

For example, the image calibration metadata associated with the `S3/VH` image can be read using
`group="S3/VH/calibration"`:

```python-repl
>>> slc_s3_vh_calibration = xr.open_dataset(slc_sm_path, group="S3/VH/calibration", engine="sentinel-1")
>>> slc_s3_vh_calibration
<xarray.Dataset>
Dimensions:       (line: 22, pixel: 476)
Coordinates:
  * line          (line) int64 0 1925 3850 5775 7700 ... 34649 36574 38499 40424
  * pixel         (pixel) int64 0 40 80 120 160 ... 18880 18920 18960 18997
Data variables:
    azimuth_time  (line) datetime64[ns] ...
    sigmaNought   (line, pixel) float32 ...
    betaNought    (line, pixel) float32 ...
    gamma         (line, pixel) float32 ...
    dn            (line, pixel) float32 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                SM
    swaths:                              ['S3']
    orbit_number:                        37258
    relative_orbit_number:               86
    ...
    stop_time:                           2021-04-01T15:29:14.277650
    group:                               /S3/VH/calibration
    Conventions:                         CF-1.8
    title:                               Calibration coefficients
    comment:                             The dataset contains calibration inf...
    history:                             created by xarray_sentinel-...

```

Note that in this case, the dimensions are `line` and `pixel` with coordinates corresponding to
the sub-grid of the original image where the calibration Look Up Table is defined.

The groups present in a typical Sentinel-1 Stripmap product are:

```
/
└─ S3
   ├─ VH
   │  ├─ orbit
   │  ├─ attitude
   │  ├─ azimuth_fm_rate
   │  ├─ dc_estimate
   │  ├─ gcp
   │  ├─ coordinate_conversion
   │  ├─ calibration
   │  ├─ noise_range
   │  └─ noise_azimuth
   └─ VV
      ├─ orbit
      ├─ attitude
      ├─ azimuth_fm_rate
      ├─ dc_estimate
      ├─ gcp
      ├─ coordinate_conversion
      ├─ calibration
      ├─ noise_range
      └─ noise_azimuth

```

## Advanced usage

### TOPS burst datasets

The IW and EW products, that use the Terrain Observation with Progressive Scan (TOPS) acquisition mode,
are more complex because they contain several beam modes in the same SAFE package,
but also because the measurement array is a collage of sub-images called *bursts*.

*xarray-sentinel* provides a helper function that crops a burst out of a measurement dataset for you.

You need to first open the desired measurement dataset, for example, the HH polarisation
of the first IW swath of the `S1A_IW_SLC__1SDH_20220414T102209_20220414T102236_042768_051AA4_E677.SAFE`
product, in the current folder:

```python-repl
>>> slc_iw_v340_path = "tests/data/S1A_IW_SLC__1SDH_20220414T102209_20220414T102236_042768_051AA4_E677.SAFE"
>>> slc_iw1_v340_hh = xr.open_dataset(slc_iw_v340_path, group="IW1/HH", engine="sentinel-1")
>>> slc_iw1_v340_hh
<xarray.Dataset>
Dimensions:           (pixel: 21169, line: 13500)
Coordinates:
  * pixel             (pixel) int64 0 1 2 3 4 ... 21164 21165 21166 21167 21168
  * line              (line) int64 0 1 2 3 4 5 ... 13495 13496 13497 13498 13499
    azimuth_time      (line) datetime64[ns] ...
    slant_range_time  (pixel) float64 ...
Data variables:
    measurement       (line, pixel) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        42768
    relative_orbit_number:               171
    ...
    geospatial_lon_min:                  -61.94949110259839
    geospatial_lon_max:                  -60.24826879672774
    group:                               /IW1/HH
    subgroups:                           ['orbit', 'attitude', 'azimuth_fm_ra...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

Note that the measurement data for IW and EW acquisition modes can not be indexed by physical
coordinates because of the collage nature of the image.

Now the 9th burst out of 9 can be cropped from the swath data using `burst_index=8`, via:

```python-repl
>>> import xarray_sentinel
>>> xarray_sentinel.crop_burst_dataset(slc_iw1_v340_hh, burst_index=8)
<xarray.Dataset>
Dimensions:           (slant_range_time: 21169, azimuth_time: 1500)
Coordinates:
    pixel             (slant_range_time) int64 0 1 2 3 ... 21166 21167 21168
    line              (azimuth_time) int64 12000 12001 12002 ... 13498 13499
  * azimuth_time      (azimuth_time) datetime64[ns] 2022-04-14T10:22:33.80763...
  * slant_range_time  (slant_range_time) float64 0.005348 0.005349 ... 0.005677
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        42768
    relative_orbit_number:               171
    ...
    group:                               /IW1/HH
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...
    azimuth_anx_time:                    2136.774327
    burst_index:                         8
    burst_id:                            365923

```

If IPF processor version is 3.40 or higher, it is also possible to select the burst
to be cropped using the `burst_id` key:

```python-repl
>>> xarray_sentinel.crop_burst_dataset(slc_iw1_v340_hh, burst_id=365923)
<xarray.Dataset>
Dimensions:           (slant_range_time: 21169, azimuth_time: 1500)
Coordinates:
    pixel             (slant_range_time) int64 0 1 2 3 ... 21166 21167 21168
    line              (azimuth_time) int64 12000 12001 12002 ... 13498 13499
  * azimuth_time      (azimuth_time) datetime64[ns] 2022-04-14T10:22:33.80763...
  * slant_range_time  (slant_range_time) float64 0.005348 0.005349 ... 0.005677
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        42768
    relative_orbit_number:               171
    ...
    group:                               /IW1/HH
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...
    azimuth_anx_time:                    2136.774327
    burst_index:                         8
    burst_id:                            365923

```

Note that the helper function also performs additional changes, such as swapping the dimensions
to the physical coordinates and adding burst attributes.

As a quick way to access burst data, you can add the `burst_index` to the group specification on
open, for example, `group="IW1/VH/8"`.
The burst groups are not listed in the `subgroup` attribute because they are not structural.

```python-repl
>>> slc_iw_v330_path = "tests/data/S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
>>> xr.open_dataset(slc_iw_v330_path, group="IW1/VH/8", engine="sentinel-1")
<xarray.Dataset>
Dimensions:           (slant_range_time: 21632, azimuth_time: 1501)
Coordinates:
    pixel             (slant_range_time) int64 ...
    line              (azimuth_time) int64 ...
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:46.27227...
  * slant_range_time  (slant_range_time) float64 0.005343 0.005343 ... 0.005679
Data variables:
    measurement       (azimuth_time, slant_range_time) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              B
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        26269
    relative_orbit_number:               168
    ...
    geospatial_lon_max:                  12.093126130070317
    group:                               /IW1/VH
    azimuth_anx_time:                    2210.634453
    burst_index:                         8
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

### Calibration

*xarray-sentinel* provides helper functions to calibrate the data using the calibration metadata.
You can compute the gamma intensity for part of the Stripmap image above with:

```python-repl
>>> xarray_sentinel.calibrate_intensity(slc_s3_vh.measurement[:2048, :2048], slc_s3_vh_calibration.gamma)
<xarray.DataArray (azimuth_time: 2048, slant_range_time: 2048)>
dask.array<pow, shape=(2048, 2048), dtype=float32, chunksize=(2048, 2048), chunktype=numpy.ndarray>
Coordinates:
    pixel             (slant_range_time) int64 dask.array<chunksize=(2048,), meta=np.ndarray>
    line              (azimuth_time) int64 dask.array<chunksize=(2048,), meta=np.ndarray>
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T15:28:55.11150...
  * slant_range_time  (slant_range_time) float64 0.005273 0.005273 ... 0.005303
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              A
    mode:                                SM
    swaths:                              ['S3']
    orbit_number:                        37258
    relative_orbit_number:               86
    ...
    geospatial_lat_min:                  -12.17883496921861
    geospatial_lat_max:                  -10.85986742252814
    geospatial_lon_min:                  42.772483374347
    geospatial_lon_max:                  43.75770573943618
    units:                               m2 m-2
    long_name:                           gamma

```

### Advanced data access via fsspec

**You need the unreleased rasterio >= 1.3.0 for fsspec to work on measurement data**

*xarray-sentinel* can read data from a variety of data stores including local file systems,
network file systems, cloud object stores and compressed file formats, like Zip.
This is done by passing *fsspec* compatible URLs to `xr.open_dataset` and optionally
the `storage_options` keyword argument.

For example you can open a product directly from a zip file with:

```python-repl
>>> slc_iw_zip_path = "tests/data/S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.zip"
>>> xr.open_dataset(f"zip://*/manifest.safe::{slc_iw_zip_path}", group="IW1/VH", engine="sentinel-1")  # doctest: +SKIP
<xarray.Dataset>
Dimensions:           (pixel: 21632, line: 13509)
Coordinates:
  * pixel             (pixel) int64 0 1 2 3 4 ... 21627 21628 21629 21630 21631
  * line              (line) int64 0 1 2 3 4 5 ... 13504 13505 13506 13507 13508
    azimuth_time      (line) datetime64[ns] ...
    slant_range_time  (pixel) float64 ...
Data variables:
    measurement       (line, pixel) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              B
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        26269
    relative_orbit_number:               168
    ...
    number_of_bursts:                    9
    lines_per_burst:                     1501
    group:                               /IW1/VH
    subgroups:                           ['orbit', 'attitude', 'azimuth_fm_ra...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

As an example of remote access, you can open a product directly from a GitHub repo with:

```python-repl
>>> xr.open_dataset(f"github://bopen:xarray-sentinel@/{slc_iw_path}", group="IW1/VH", engine="sentinel-1")  # doctest: +SKIP
<xarray.Dataset>
Dimensions:           (pixel: 21632, line: 13509)
Coordinates:
  * pixel             (pixel) int64 0 1 2 3 4 ... 21627 21628 21629 21630 21631
  * line              (line) int64 0 1 2 3 4 5 ... 13504 13505 13506 13507 13508
    azimuth_time      (line) datetime64[ns] ...
    slant_range_time  (pixel) float64 ...
Data variables:
    measurement       (line, pixel) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              B
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        26269
    relative_orbit_number:               168
    ...
    number_of_bursts:                    9
    lines_per_burst:                     1501
    group:                               /IW1/VH
    subgroups:                           ['orbit', 'attitude', 'azimuth_fm_ra...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

*fsspec* is very powerful and supports caching and chaining, for example you can open a
zip file off a GitHub repo and cache the file locally with:

```python-repl
>>> xr.open_dataset(
...     f"zip://*/manifest.safe::simplecache::github://bopen:xarray-sentinel@/{slc_iw_zip_path}",
...     engine="sentinel-1",
...     group="IW1/VH",
...     storage_options={
...         "simplecache": {"cache_storage": "/tmp/zipfiles/"},
...     },
... )  # doctest: +SKIP
<xarray.Dataset>
Dimensions:           (pixel: 21632, line: 13509)
Coordinates:
  * pixel             (pixel) int64 0 1 2 3 4 ... 21627 21628 21629 21630 21631
  * line              (line) int64 0 1 2 3 4 5 ... 13504 13505 13506 13507 13508
    azimuth_time      (line) datetime64[ns] ...
    slant_range_time  (pixel) float64 ...
Data variables:
    measurement       (line, pixel) complex64 ...
Attributes: ...
    family_name:                         SENTINEL-1
    number:                              B
    mode:                                IW
    swaths:                              ['IW1', 'IW2', 'IW3']
    orbit_number:                        26269
    relative_orbit_number:               168
    ...
    number_of_bursts:                    9
    lines_per_burst:                     1501
    group:                               /IW1/VH
    subgroups:                           ['orbit', 'attitude', 'azimuth_fm_ra...
    Conventions:                         CF-1.8
    history:                             created by xarray_sentinel-...

```

## Reference documentation

This is the list of the reference documents:

- Sentinel-1 document library:
  - [user guides](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar)
  - [technical guides](https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-1-sar)
- [Sentinel-1 Product Specification v3.9 07 May 2021 S1-RS-MDA-52-7441-3-9 documenting IPF 3.40](https://sentinel.esa.int/documents/247904/1877131/S1-RS-MDA-52-7441-3-9-2_Sentinel-1ProductSpecification.pdf)
- [Sentinel-1 Product Specification v3.7 27 February 2020 S1-RS-MDA-52-7441 documenting IPF 3.30](https://sentinel.esa.int/documents/247904/1877131/Sentinel-1-Product-Specification)
- [Radiometric Calibration of S-1 Level-1 Products Generated by the S-1 IPF v1.0 21/05/2015 ESA-EOPG-CSCOP-TN-0002](https://sentinel.esa.int/documents/247904/685163/S1-Radiometric-Calibration-V1.0.pdf)

## Design decisions

- The main design choice for *xarray-sentinel* is for it to be as much as viable a pure map of
  the content of the SAFE data package, with as little interpretation as possible.
  - The tree-like structure follows the structure of the SAFE package even when information,
    like orbit and attitude, is expected to be identical for different beam modes.
    We observed at least a case where the number of orbital state vectors reported
    was different between beam modes.
  - Data and metadata are converted to the closest available data-type in *Python* / *numpy*.
    The most significant conversion is from `CInt16` to `np.complex64` for the SLC measurements
    that double the space requirements for the data.
    Also, *xarray-sentinel* converts UTC times to `np.datetime64` and makes no attempt to support
    *leap seconds*, acquisitions containing leap seconds may crash or silently return corrupted data.
    See the rationale for choices of the coordinates data-types below.
  - We try to keep all naming as close as possible to the original names.
    In particular, for metadata we use the names of the XML tags, only converting them
    from *camelCase* to *snake_case*.
- Whenever possible *xarray-sentinel* indexes the data with physical coordinates
  `azimuth_time` and `slant_range_time`, but keeps image `line` and `pixel` as auxiliary coordinates.
- As an exception to the metadata naming rule above we add some attributes to get
  CF-Conventions compliance.
- We aim at opening available data and metadata even for partial SAFE packages, for example,
  *xarray-sentinel* can open a measurement dataset for a beam mode even when the TIFF files of other
  beam modes / polarizations are missing.
- Accuracy considerations and rationale for coordinates data-types:
  - `azimuth_time` can be expressed as `np.datetime64[ns]` since
    spatial resolution at LEO speed is 10km/s * 1ns ~= 0.001cm.
  - `slant_range_time` on the other hand cannot be expressed as `np.timedelta64[ns]` as
    spatial resolution at the speed of light is 300_000km/s * 1ns / 2 ~= 15cm,
    i.e. not enough for interferometric applications.
    `slant_range_time` needs a spatial resolution of 0.001cm at a 1_000km distance,
    i.e. around 1e-9, well within the 1e-15 resolution of IEEE-754 float64.

## Project badges

[![on-push](https://github.com/bopen/xarray-sentinel/actions/workflows/on-push.yml/badge.svg)](https://github.com/bopen/xarray-sentinel/actions/workflows/on-push.yml)
[![codecov](https://codecov.io/gh/bopen/xarray-sentinel/branch/main/graph/badge.svg?token=OLw9it0i18)](https://codecov.io/gh/bopen/xarray-sentinel)

## Contributing

The main repository is hosted on GitHub.
Testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/bopen/xarray-sentinel

Lead developers:

- [Aureliana Barghini](https://github.com/aurghs) - [B-Open](https://www.bopen.eu)
- [Alessandro Amici](https://github.com/alexamici) - [B-Open](https://www.bopen.eu)

Main contributors:

- [Corrado Avolio](https://github.com/corrado9999) - [e-GEOS](https://www.e-geos.it)

See also the list of [contributors](https://github.com/bopen/xarray-sentinel/contributors) who participated in this project.

## Sponsoring

[B-Open](https://bopen.eu) commits to maintain the project long term and we are happy to accept sponsorships to develop new features.

We wish to express our gratitude to the project sponsors:

- [Microsoft](https://microsoft.com) has sponsored the support for *GRD* products and *fsspec* data access.

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
