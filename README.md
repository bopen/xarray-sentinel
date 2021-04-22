# xarray-sentinel

**WARNING: this product is a "technology preview" / pre-Alpha**

Xarray backend to explore and load Copernicus Sentinel-1 satellite data products.

This Open Source project is sponsored by B-Open - https://www.bopen.eu

## Install

The easiest way to install *xarray-sentinel* is via *conda*.
Create a new environment, activate it, install the package and its dependencies,
as follows:

```shell
    conda create -n xarray-sentinel
    conda activate xarray-sentinel
    conda install -c conda-forge rioxarray xmlschema
    pip install xarray-sentinel
```

## Product support status:

- Sentinel-1 SLC IW (Interferometric Wide Swath): **work-in-progress**
- Sentinel-1 SLC EW (Extended Wide Swath): in roadmap
- Sentinel-1 SLC SM (Stripmap): in roadmap
- Sentinel-1 GRD SM/IW/EW: in roadmap
- Sentinel-2 L1C/L2A: in roadmap


## Sentinel-1 SLC IW

### Data

Currently, xarray-sentinel provides access as Xarray datasets to the following data:

- burst data
- gcp
- orbit
- attitude

using `azimuth_time` and `slant_range_time` dimensions.


## Examples:

### Open root dataset

```python-repl
>>> from xarray_sentinel import sentinel1
>>> product_path = "tests/data/S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
>>> sentinel1.open_dataset(product_path)
<xarray.Dataset>
Dimensions:  ()
Data variables:
    *empty*
Attributes: (12/15)
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    sar:polarizations:          ['VV', 'VH']
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    groups:                     ['IW1', 'IW1/gcp', 'IW1/attitude', 'IW1/orbit...
    Conventions:                CF-1.7
    history:                    created by xarray_sentinel-...

```

the attribute `groups` shows the available groups to be loaded. The key `group`
shall be used to select the dataset to be loaded.

### Open gcp dataset

To load the gcp relative to the first swath use the key `group="IW1/gcp"`:
```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/gcp")
<xarray.Dataset>
Dimensions:           (azimuth_time: 10, slant_range_time: 21)
Coordinates:
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:24.20973...
  * slant_range_time  (slant_range_time) float64 0.005343 0.00536 ... 0.005679
Data variables:
    latitude          (azimuth_time, slant_range_time) float64 ...
    longitude         (azimuth_time, slant_range_time) float64 ...
    height            (azimuth_time, slant_range_time) float64 ...
    incidenceAngle    (azimuth_time, slant_range_time) float64 ...
    elevationAngle    (azimuth_time, slant_range_time) float64 ...
Attributes:
    Conventions:  CF-1.7
    title:        Geolocation grid
    comment:      The dataset contains geolocation grid point entries for eac...
    history:      created by xarray_sentinel-...

```

### Open attitude dataset

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/attitude")
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
Attributes:
    Conventions:  CF-1.7
    title:        Attitude information used by the IPF during processing
    comment:      The dataset contains a sets of attitude data records that a...
    history:      created by xarray_sentinel-...

```

### Open orbit dataset

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/orbit")
<xarray.Dataset>
Dimensions:       (azimuth_time: 17)
Coordinates:
  * azimuth_time  (azimuth_time) datetime64[ns] 2021-04-01T05:25:19 ... 2021-...
Data variables:
    x             (azimuth_time) float64 ...
    y             (azimuth_time) float64 ...
    z             (azimuth_time) float64 ...
    vx            (azimuth_time) float64 ...
    vy            (azimuth_time) float64 ...
    vz            (azimuth_time) float64 ...
Attributes:
    reference_system:  Earth Fixed
    Conventions:       CF-1.7
    title:             Orbit information used by the IPF during processing
    comment:           The dataset contains a sets of orbit state vectors tha...
    history:           created by xarray_sentinel-...

```

### Open a single burst

```python-repl
>>> sentinel1.open_dataset(product_path, group="IW1/R168-N459-E0115")
<xarray.Dataset>
Dimensions:           (azimuth_time: 1501, slant_range_time: 21632)
Coordinates:
  * azimuth_time      (azimuth_time) datetime64[ns] 2021-04-01T05:26:43.51577...
  * slant_range_time  (slant_range_time) float64 0.005343 0.005343 ... 0.005679
Data variables:
    VH                (azimuth_time, slant_range_time) complex128 ...
    VV                (azimuth_time, slant_range_time) complex128 ...
Attributes: (12/14)
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    sar:instrument_mode:        IW
    sar:polarizations:          ['VV', 'VH']
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    Conventions:                CF-1.7
    history:                    created by xarray_sentinel-...

```

With the upcoming release of Xarray v0.18.0, xarray-sentinel will be automatically available as
an Xarray bakend:
 
```python-repl
>>> import xarray as xr
>>> ds = xr.open_dataset(product_path, engine="sentinel-1")

```


## Contributing

The main repository is hosted on GitHub,
testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/bopen/xarray-sentinel

Lead developer:

- [Aureliana Barghini](https://github.com/aurghs) - [B-Open](https://www.bopen.eu/)

Main contributors:

- [Alessandro Amici](https://github.com/alexamici) - [B-Open](https://www.bopen.eu/)
- [Corrado Avolio](https://github.com/corrado9999) - [e-GEOS](https://www.e-geos.it/)

See also the list of [contributors](https://github.com/bopen/xarray-sentinel/contributors) who participated in this project.


## License

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
