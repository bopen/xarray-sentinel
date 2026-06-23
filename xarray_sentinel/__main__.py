import distributed
import typer

import xarray_sentinel.reformat

app = typer.Typer()


@app.command()
def convert(source: str, target: str) -> None:
    groups = {
        "IW/VV": "IW/VV",
        "IW/VH": "IW/VH",
    }
    client = distributed.Client(processes=True)
    print(client)
    xarray_sentinel.reformat.to_group_zarr(source, target, groups=groups)


@app.command()
def info() -> None:
    pass


if __name__ == "__main__":
    app()
