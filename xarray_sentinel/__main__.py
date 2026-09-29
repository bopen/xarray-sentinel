import importlib.metadata

import typer

import xarray_sentinel.reformat

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
def convert(source: str, target: str) -> None:
    groups = {
        "IW/VV": "IW/VV",
        "IW/VH": "IW/VH",
    }
    import distributed

    distributed.Client(processes=True)  # type: ignore
    xarray_sentinel.reformat.to_group_zarr(source, target, groups=groups)


@app.command()
def info() -> None:
    pass


if __name__ == "__main__":
    app()
