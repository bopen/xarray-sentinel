#!/bin/sh

mkdir -p data

# SM

## SLC
sentinelsat --path data -d --include-pattern "*vv*" \
  --name S1B_S6_SLC__1SDV_20211216T115438_20211216T115501_030050_03968A_4DCB

## GRD
sentinelsat --path data -d --include-pattern "*vv*" \
  --name S1B_S6_GRDH_1SDV_20211216T115438_20211216T115501_030050_03968A_0F8A

## GRD zipped to test fsspec
sentinelsat --path data -d \
  --name S1B_S6_GRDH_1SDV_20211216T115438_20211216T115501_030050_03968A_0F8A


# IW

## SLC
sentinelsat --path data -d --include-pattern "*iw3*vv*" \
  --name S1B_IW_SLC__1SDV_20211223T051121_20211223T051148_030148_039993_BA4B

## GRD
sentinelsat --path data -d --include-pattern "*vv*" \
  --name S1B_IW_GRDH_1SDV_20211223T051122_20211223T051147_030148_039993_5371
