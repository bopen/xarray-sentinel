#!/bin/bash

echo "Uncomment to download the full products, the unzip manually"

if [ -z "$SCIHUB_CREDENTIALS" ]
then
  echo "define the SCIHUB_CREDENTIALS environment virable as user:password";
  exit 1
fi

# Sentinel-1 SLC IW
# curl -u $SCIHUB_CREDENTIALS -L -o S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('cb28c2e3-f258-4af0-96a7-9af05a82cc5c')/\$value"

# Sentinel-1 SLC SM S6
# curl -u $SCIHUB_CREDENTIALS -L -o S1A_S6_SLC__1SDV_20210402T115512_20210402T115535_037271_046407_39FD.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('d45c1d65-5bd9-4ccf-a882-aff206a5c157')/\$value"

# Sentinel-1 SLC SM S3
# curl -u $SCIHUB_CREDENTIALS -L -o S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('8a5251d4-490a-4669-9702-57d844c7ee77')/\$value"

# Sentinel-1 SLC EW
# curl -u $SCIHUB_CREDENTIALS -L -o S1A_EW_SLC__1SDH_20210403T122536_20210403T122630_037286_046484_8152.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('4e237863-7cf3-4110-8a28-744d2b80a21c')/\$value"

# Sentinel-1 SLC WV
# curl -u $SCIHUB_CREDENTIALS -L -o S1B_WV_SLC__1SSV_20210403T083025_20210403T084452_026300_032390_D542.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('a3660e2f-bd85-47f0-9ab2-2467c13689c5')/\$value"

# Sentinel-1 GRD IW
# curl -u $SCIHUB_CREDENTIALS -L -o S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('93265069-4d8e-4c6e-926c-73cff7bc605f')/\$value"

# Sentinel-2 S2MSI1C
# curl -u $SCIHUB_CREDENTIALS -L -o S2A_MSIL1C_20210403T101021_N0300_R022_T33TUM_20210403T110551.zip "https://scihub.copernicus.eu/dhus/odata/v1/Products('4c14fd90-6a4a-42f4-a484-abf1df711ed0')/\$value"
