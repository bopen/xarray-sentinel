# Tentative data-tree structure

Sentinel-1 SLC IW product structure:

```
/
├─ IW1
│  ├─ VH
│  │  ├─ line (line)
│  │  ├─ pixel (pixel)
│  │  ├─ slant_range_time (pixel)
│  │  ├─ measurement (line, pixel)
│  │  ├─ gcp
│  │  │  ├─ azimuth_time (azimuth_time)
│  │  │  ├─ slant_range_time (slant_range_time)
│  │  │  ├─ line (azimuth_time)
│  │  │  ├─ pixel (slant_range_time)
│  │  │  ├─ latitude (azimuth_time, slant_range_time)
│  │  │  ├─ longitude (azimuth_time, slant_range_time)
│  │  │  ├─ height (azimuth_time, slant_range_time)
│  │  │  ├─ incidenceAngle (azimuth_time, slant_range_time)
│  │  │  └─ elevationAngle (azimuth_time, slant_range_time)
│  │  ├─ orbit
│  │  │  ├─ azimuth_time (azimuth_time)
│  │  │  ├─ axis (axis)  # "x", "y", "z"
│  │  │  ├─ position (azimuth_time, axis)
│  │  │  └─ velocity (azimuth_time, axis)
│  │  ├─ attitude
│  │  │  ├─ azimuth_time (azimuth_time)
│  │  │  ├─ q0 (azimuth_time)
│  │  │  ├─ q1 (azimuth_time)
│  │  │  ├─ q2 (azimuth_time)
│  │  │  ├─ q3 (azimuth_time)
│  │  │  ├─ wx (azimuth_time)
│  │  │  ├─ wy (azimuth_time)
│  │  │  ├─ wz (azimuth_time)
│  │  │  ├─ pitch (azimuth_time)
│  │  │  ├─ roll (azimuth_time)
│  │  │  └─ yaw (azimuth_time)
│  │  ├─ calibration
│  │  │  ├─ azimuth_time (line)
│  │  │  ├─ line (line)
│  │  │  ├─ pixel (pixel)
│  │  │  ├─ sigmaNought (line, pixel)
│  │  │  ├─ betaNought (line, pixel)
│  │  │  ├─ gamma (line, pixel)
│  │  │  └─ dn (line, pixel)

# do we need the following as virtual structures?

│  │  ├─ R168-N459-E0115  # format is f"R{relative_orbit:03}-{N_or_S}{lat:03}-{E_or_W}{lon:04}"
│  │  │  ├─ azimuth_time (azimuth_time)
│  │  │  ├─ slant_range_time (slant_range_time)
│  │  │  ├─ line (azimuth_time)
│  │  │  ├─ pixel (slant_range_time)
│  │  │  ├─ R168-N459-E0115 (azimuth_time, slant_range_time)  # "measurements" or "VH-R168-N459-E0115"?
│  │  │  ├─ gcp  # GPCs relative to the burst?
│  │  │  │  ├─ azimuth_time (azimuth_time)
│  │  │  │  ├─ slant_range_time (slant_range_time)
│  │  │  │  ├─ line (azimuth_time)
│  │  │  │  ├─ pixel (slant_range_time)
│  │  │  │  ├─ latitude (azimuth_time, slant_range_time)
│  │  │  │  ├─ longitude (azimuth_time, slant_range_time)
│  │  │  │  ├─ height (azimuth_time, slant_range_time)
│  │  │  │  ├─ incidenceAngle (azimuth_time, slant_range_time)
│  │  │  │  └─ elevationAngle (azimuth_time, slant_range_time)
│  │  │  └─ calibration  # calibration relative to the burst?
│  │  │     ├─ azimuth_time (line)
...
```
