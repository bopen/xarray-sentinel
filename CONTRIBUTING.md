Setup the base `XARRAY-SENTINEL` conda environment and update it to include development dependencies with:

```
cd xarray-sentinel
conda create -n XARRAY-SENTINEL -c conda-forge python=3.9 mamba
conda activate XARRAY-SENTINEL
make conda-env-update-all CONDA=mamba CONDAFLAGS=
pip install -U --pre --no-binary rasterio rasterio==1.3a3  # for fsspec support
```

Download sample data and run the notebooks:

```
cd notebooks
DHUS_USER=your_scihub_username DHUS_PASSWORD=your_scihub_password ./download_data.sh
```