"""Download the S3 SAFE products of a benchmark configuration to ``benchmarks/data``.

Run with any Python 3.11+ and the AWS CLI, only the missing files are transferred:

    python benchmarks/download.py benchmarks/config.toml
"""

import argparse
import subprocess
import tomllib
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", type=Path, help="TOML configuration file")
    args = parser.parse_args()
    path = args.config.resolve()
    with path.open("rb") as file:
        config = tomllib.load(file)

    uv_run = ["uv", "run", "--no-project"]
    if "env_file" in config:
        uv_run += ["--env-file", str(path.parent / config["env_file"])]
    for product in config["products"]:
        if product.startswith("s3://"):
            target = DATA / Path(product.rstrip("/")).name
            subprocess.run(
                [*uv_run, "aws", "s3", "sync", product, str(target)], check=True
            )


if __name__ == "__main__":
    main()
