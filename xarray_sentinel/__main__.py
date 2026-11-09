import json
import warnings

import click
import xarray as xr

from . import eopf_product


@click.group("xarray-sentinel")
@click.version_option(package_name="xarray-sentinel", prog_name="xarray-sentinel")
def app() -> None:
    pass


@app.command("to-eopf-zarr")
@click.argument("source")
@click.argument("target")
def to_eopf_zarr(source: str, target: str) -> None:
    """Convert a SAFE product to EOPF Zarr.

    Convert the Sentinel-1 SAFE product SOURCE to the EOPF Zarr product TARGET,
    replacing TARGET if it exists.

    \b
    Arguments:
      SOURCE  Path or fsspec URL of the Sentinel-1 SAFE product.
      TARGET  Path or fsspec URL of the output EOPF Zarr product.
    """  # noqa: D301 click needs the backspace in "\b" to keep the lines
    try:
        import zarr
    except ModuleNotFoundError:
        raise click.ClickException(
            "to-eopf-zarr needs the 'zarr' extra, install it with:\n"
            "  pip install 'xarray-sentinel[zarr]'\n"
            "or run the command with:\n"
            "  uvx 'xarray-sentinel[zarr]' to-eopf-zarr SOURCE TARGET"
        )

    try:
        from zarr.errors import ZarrUserWarning
    except ImportError:  # zarr < 3.1.2
        ZarrUserWarning = UserWarning  # type: ignore

    # the EOPF products have consolidated metadata, not yet in the Zarr 3 spec
    warnings.filterwarnings("ignore", category=ZarrUserWarning)
    # and fixed length strings as well, zarr 3.1 warns about them
    warnings.filterwarnings("ignore", message="The data type .* Zarr V3 specification")

    with xr.open_datatree(source, engine="sentinel-1") as datatree:
        datatree.to_zarr(target, mode="w", consolidated=False)
        zarr.consolidate_metadata(target)


@app.command()
@click.argument("source")
def info(source: str) -> None:
    """Print the STAC metadata of a SAFE product.

    Print the product level STAC item of the Sentinel-1 SAFE product SOURCE,
    reading only the manifest.

    \b
    Arguments:
      SOURCE  Path or fsspec URL of the Sentinel-1 SAFE product.
    """  # noqa: D301 click needs the backspace in "\b" to keep the lines
    stac_item = eopf_product.open_stac_item(source)
    click.echo(json.dumps(stac_item, indent=2))


if __name__ == "__main__":
    app()
