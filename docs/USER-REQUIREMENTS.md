
Data groups:

- SLC complex measurements by swath and burst
  - azimuth / time, slant_range as dimensions, polarisation as variables
  - azimuth / slant_range coordinates as distances instead of times for
    easier interpretation? (slant_range == two-ways-time * speed-of-light,
    azimuth as linear distance from ascending node?)
  - keep time coordinates as UTC, TAI, UT1 and elapsed time from ascending node (NOT PRESENT??)
- calibration information (azimuth / slant_range dimensions on a reduced grid)
- ground control points (azimuth / slant_range dimensions on one more reduced grid)
- de-ramping parameters
- kinematic description:
  - orbit / state vectors
  - attitude / quaternions
- antenna pattern
- Doppler centroid / Doppler rate
- incidence angle & Co. 

Not loaded:
- noise

Attributes:

- mission, acquisition, processing, etc

Conformance:

- CF conventions for the coordinates (with special attentions to time)
- STAC metadata for attributes with SAT and SAR extensions

High level requirements:

- keep all naming as close to the original al possible (with XML camel case to Python snake case?)
- support opening a swath when other swaths are missing (especially the tifs)


# User experience

```python
>>> ds = xr.open_dataset("S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE/manifest.safe")
>>> ds = xr.open_dataset("S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE")
>>> ds
... instruction on what to do ...

>>> ds_iw1_gpc = xr.open_dataset("S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE", group="IW1/gpc")
>>> ds_iw1_gpc = xr.open_dataset("S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE/annotations/s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml", group="gcp")
```

Structure:

* root / SAFE
  * swaths "IW1" "IW2" "S3" etc / duplicated in VH-VV annotation XML
    * bursts "R022_N433_E0120" etc
      * polarizations are data variables
    * gcp "gcp"
    * calibration "calibration"
    * orbit "orbit" / duplicated in annotation XML for different polarizations
    * attitude "attitude" / same as above
    * antenna pattern "antenna"
    * zero-Doppler "doppler"

examples: `group="IW2/orbit"`, `group="IW2/N433_E0120`, `group="S3/gcp"` etc

Dimensions, coordinates and variables

We may either keep names and unit of measures as close as possible to the original
or going for easier-to-use choices.

In all cases we add the XML tag name in the long_name so it is clear the provenance of the
information: e.g. for `slant_range_time` -> `"long_name": "two way delay (slantRangeTime)"`

* `azimuth_time` as CF time in UTC (warn: may fail on leap seconds)
* `slant_range_time` as CF time interval in `"s"`


# Accuracy considerations

- `azimuth_time` can be expressed as `np.datetime64[ns]` because
  spatial resolution at LEO speed is 10km/s * 1ns ~= 0.001cm
- `slant_range_time` cannot be expressed as `np.timedelta64[ns]` because
  spatial resolution at the speed of light is 300_000km/s * 1ns / 2 ~= 15cm,
  that it is not enough for interferometric applications.
  `slant_range_time` needs a spatial resolution of 0.001cm at a 1_000km distance
  so around 1e-9 that is well within 1e-15 resolution of IEEE-754 float64.

