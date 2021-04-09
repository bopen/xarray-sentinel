
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

- support opening a swath when other swaths are missing (especially the tifs)


User experience
---------------

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
  * orbit-attitude "orbit" / (almost) duplicated in all annotation XML
  * swaths "IW1" "IW2" "S3" etc / duplicated in VH-VV annotation XML
    * bursts / polarization "N433_W0120_VV" etc (include polarization?)
    * gcp "gcp"
    * calibration "calibration"
    * antenna pattern "antenna"
    * zero-Doppler "doppler"

examples: `group="orbit"`, `group="IW2/N433_W0120_VV`, `group="S3/gcp"` etc

Dimensions, coordinates and variables

We may either keep names and unit of measures as close as possible to the original
or going for easier-to-use chaices.

In all cases we add the XML tag name in the long_name so it is clear the provenance of the
information: e.g. for `slant_range_time` -> `"long_name": "two way delay (slantRangeTime)""`

* `azimuth_time` as CF time in UTC (warn: may fail on leap seconds)
* `slant_range_time` as CF time interval in "s"
