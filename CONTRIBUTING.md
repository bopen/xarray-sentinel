Setup the base `XARRAY-SENTINEL` conda environment and update it to include development dependencies with:

```
cd xarray-sentinel
conda create -n XARRAY-SENTINEL -c conda-forge python=3.9 mamba
conda activate XARRAY-SENTINEL
make conda-env-update-all CONDA=mamba CONDAFLAGS=
pip install -e .
pip install -U --pre --no-deps --no-binary rasterio "rasterio>=1.3a3"  # for fsspec support
```

Download sample data and run the notebooks:

```
cd notebooks
DHUS_USER=<user> DHUS_PASSWORD=<password> ./download_data.sh
jupyter notebook
```
