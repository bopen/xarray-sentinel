Setup the base `XARRAY-SENTINEL` conda environment and update it to include development dependencies with:

```
make conda-env-create
make conda-env-update-all
conda activate XARRAY-SENTINEL
```

Note that to update the environment when it is already activated you need to use:

```
make conda-env-update-all CONDAFLAGS=
```
