
mkdir -p data

# SLC SM
sentinelsat --path data -d --include-pattern "*vv*" \
  --name S1B_S6_SLC__1SDV_20211216T115438_20211216T115501_030050_03968A_4DCB

# SLC IW
sentinelsat --path data -d --include-pattern "*iw3*vv*" \
  --name S1B_IW_SLC__1SDV_20211223T051121_20211223T051148_030148_039993_BA4B
