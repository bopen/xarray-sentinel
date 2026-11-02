This project is Free and Open Source Software released under the terms of the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
Contributions are highly welcomed and appreciated. Every little bit of help counts, so do not hesitate!

## Report a bug

If you encounter any problems, please file a bug report
in the project [issue tracker](https://github.com/bopen/xarray-sentinel/issues)
along with a detailed description.

## Submit a pull request

Development dependencies are installed and the environment kept up to date by
[uv](https://docs.astral.sh/uv/):

```shell
uv sync
```

The `Makefile` wraps the common development tasks:

```shell
make              # qa + unit-tests + check-typing
make qa           # run all pre-commit hooks and deptry
make unit-tests   # run the tests with coverage
make doc-tests    # run the examples in README.md
make docs-build   # build the Sphinx documentation in docs/_build
```

Please ensure the coverage at least stays the same before you submit a pull request.

The SAFE products in `tests/data` are trimmed: most measurement and annotation files are
missing, so the tests open them with `check_files_exist=True`.

## Run the notebooks

The notebooks read the products from the Copernicus Data Space Ecosystem S3 store.
`make lab` creates `.env` from `.env.in`, where you add your
[CDSE S3 credentials](https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials),
and starts JupyterLab with it:

```shell
make lab
```

When `.env.in` changes, `make lab` replaces `.env` and keeps the old one as `.env~`.

## Keeping dependencies up to date

The `uv.lock` file pins all dependencies to ensure reproducibility,
to upgrade them to the latest allowed versions run:

```shell
uv lock --upgrade
uv sync
```

New versions are only picked up one week after their release, see `exclude-newer` in
`pyproject.toml`.
