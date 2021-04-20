# xarray-sentinel

Xarray backend to explore and load Copernicus Sentinel-1 satellite data products


## Product support status:
- Sentinel-1 SLC IWS (Interferometric Wide Swath): work-in-progress
- Sentinel-1 SLC EWS (Extended Wide Swath): in roadmap
- Sentinel-1 SLC SM (Stripmap): in roadmap
- Sentinel-1 GRD SM/IWS/EWS: in roadmap
- Sentinel-2 L1C/L2A: in roadmap


## Sentinel-1 SLC IWS

### Data  
Currently, xarray-sentinel provides access as Xarray datsets to the following data:
- burst data
- gcp
- orbit
- attitude

using `aximuth_time` and `slant_range_time` refence system.


## Examples:

### Open root dataset
```python
>>> xr.open_dataset(product_path, engine="sentinel-1")
Dimensions:  ()
Data variables:
    *empty*
Attributes: (12/13)
    constellation:              sentinel-1
    platform:                   sentinel-1b
    instrument:                 ['c-sar']
    sat:orbit_state:            descending
    sat:absolute_orbit:         26269
    sat:relative_orbit:         168
    ...                         ...
    sar:frequency_band:         C
    sar:instrument_mode:        IW
    sar:polarizations:          ['VV', 'VH']
    sar:product_type:           SLC
    xs:instrument_mode_swaths:  ['IW1', 'IW2', 'IW3']
    groups:                     ['IW1', 'IW1/gcp', 'IW1/attitude', 'IW1/orbit...
```
the attributes `groups` shows the avaible groups to be loaded. The key `group`
shall be used to select the dataset to be loaded.

### Open gcp dataset
To load the gcp relative to the first swath use the key `group="IW1/gcp"`:
```python
>>> xr.open_dataset(product_path, engine="sentinel-1", group="IW1/gcp")
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
```
### Open attitude dataset
```python
>>> xr.open_dataset(product_path, engine="sentinel-1", group="IW1/attitude")
<xarray.Dataset>
Dimensions:  (time: 25)
Coordinates:
  * time     (time) datetime64[ns] 2021-04-01T05:26:24.750001 ... 2021-04-01T...
Data variables:
    q0       (time) float64 ...
    q1       (time) float64 ...
    q2       (time) float64 ...
    wx       (time) float64 ...
    wy       (time) float64 ...
    wz       (time) float64 ...
    pitch    (time) float64 ...
    roll     (time) float64 ...
    yaw      (time) float64 ...
Attributes:
    Conventions:  CF-1.7
```

### Open orbit dataset
```python
>>> xr.open_dataset(product_path, engine="sentinel-1", group="IW1/attitude")
<xarray.Dataset>
Dimensions:  (time: 17)
Coordinates:
  * time     (time) datetime64[ns] 2021-04-01T05:25:19 ... 2021-04-01T05:27:59
Data variables:
    x        (time) float64 ...
    y        (time) float64 ...
    z        (time) float64 ...
    vx       (time) float64 ...
    vy       (time) float64 ...
    vz       (time) float64 ...
Attributes:
    Conventions:       CF-1.7
    reference_system:  Earth Fixed
```
