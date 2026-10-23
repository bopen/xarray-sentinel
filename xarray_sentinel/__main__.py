import importlib.metadata

import typer
import xarray as xr

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
    import distributed

    distributed.Client(processes=True)  # type: ignore
    datatree = xr.open_datatree(
        source, engine="sentinel-1", rasterio_chunks={"y": 2048}
    )
    datatree.to_zarr(target, mode="w")


@app.command()
def info() -> None:
    pass


if __name__ == "__main__":
    app()
