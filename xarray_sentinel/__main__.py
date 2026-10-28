import importlib.metadata
import json
import warnings

import typer
import xarray as xr
import zarr

from . import eopf_product

try:
    from zarr.errors import ZarrUserWarning
except ImportError:  # zarr < 3.1.2
    ZarrUserWarning = UserWarning  # type: ignore

# the EOPF products have consolidated metadata, not yet in the Zarr 3 spec
warnings.filterwarnings("ignore", category=ZarrUserWarning)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        version = importlib.metadata.version("xarray-sentinel")
        typer.echo(f"xarray-sentinel, version {version}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    pass


@app.command()
def convert(
    source: str = typer.Argument(..., help="Path to the Sentinel-1 SAFE product."),
    target: str = typer.Argument(..., help="Path to the output EOPF Zarr product."),
) -> None:
    """Convert a Sentinel-1 SAFE product to an EOPF Zarr product."""
    with xr.open_datatree(source, engine="sentinel-1") as datatree:
        datatree.to_zarr(target, mode="w", consolidated=False)
        zarr.consolidate_metadata(target)


@app.command()
def info(
    source: str = typer.Argument(..., help="Path to the Sentinel-1 SAFE product."),
) -> None:
    """Print the STAC metadata of the EOPF product."""
    stac_item = eopf_product.open_stac_item(source)
    typer.echo(json.dumps(stac_item, indent=2))


if __name__ == "__main__":
    app()
