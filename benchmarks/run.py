"""Benchmark the SAFE to EOPF Zarr conversion of the xarray-sentinel and eopf CLIs.

Run with any Python 3.11+, the tools run in their own uv environments:

    python benchmarks/run.py benchmarks/config.toml

The products, the operations and the tools are selected in the configuration file.
Each run appends a JSON record to ``benchmarks/results/<label>.jsonl``.

With ``--profile DIR`` the xarray-sentinel runs are profiled with pyinstrument on the
synchronous dask scheduler, so all the work is sampled but the times are not
comparable. View the sessions written to DIR with ``pyinstrument --load FILE``.
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

BENCHMARKS = Path(__file__).resolve().parent
TOOLS = ["xarray-sentinel", "eopf"]
# the GDAL configuration options, the S3 read controls of .env.in are tuned for
# xarray-sentinel, the other tools run with the GDAL defaults
GDAL_PREFIXES = ("GDAL_", "CPL_", "VSI_", "GTIFF_")
GDAL_TOOLS = {"xarray-sentinel"}

# the CLI arguments of each tool supporting the operation
OPERATIONS = {
    "info": {
        "xarray-sentinel": ["info", "{source}"],
    },
    "convert": {
        "xarray-sentinel": ["convert", "{source}", "{target}"],
        "eopf": ["convert", "{source}", "{target}"],
    },
    "convert-staged": {
        "eopf": ["convert", "{source}", "{target}", "--stage-source"],
    },
}


def tool_command(tool: str, *args: str, profile: Path | None = None) -> list[str]:
    uv_run = ["uv", "run", "--frozen"]
    if tool == "xarray-sentinel":
        uv_run += ["--extra", "lab", "--project", str(BENCHMARKS.parent)]
    else:
        uv_run += ["--project", str(BENCHMARKS / "eopf")]
    executable = [tool]
    if profile is not None:
        session = f"{profile}.pyisession"
        module = tool.replace("-", "_")
        executable = ["pyinstrument", "-r", "session", "-o", session, "-m", module]
    return [*uv_run, *executable, *args]


def host_info() -> dict[str, Any]:
    memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory": memory,
    }


def read_env_file(path: Path) -> dict[str, str]:
    environ = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            environ[key.strip()] = value.strip().strip("'\"")
    return environ


def tool_environ(tool: str, env_file: Path | None) -> dict[str, str]:
    environ = dict(os.environ)
    if env_file is not None:
        environ.update(read_env_file(env_file))
    if tool not in GDAL_TOOLS:
        environ = {k: v for k, v in environ.items() if not k.startswith(GDAL_PREFIXES)}
    return environ


def recorded_environ(environ: dict[str, str]) -> dict[str, str]:
    # the settings of the run, not the credentials
    prefixes = ("DASK_", "EOPF_", *GDAL_PREFIXES)
    return {k: v for k, v in environ.items() if k.startswith(prefixes)}


def measure(command: list[str], env: dict[str, str]) -> dict[str, Any]:
    start = time.perf_counter()
    process = subprocess.Popen(command, env=env)
    _, status, rusage = os.wait4(process.pid, 0)
    wall_time = time.perf_counter() - start
    process.returncode = os.waitstatus_to_exitcode(status)
    max_rss = rusage.ru_maxrss
    if sys.platform != "darwin":
        max_rss *= 1024
    return {
        "returncode": process.returncode,
        "wall_time": wall_time,
        "cpu_time": rusage.ru_utime + rusage.ru_stime,
        "max_rss": max_rss,
    }


def directory_size(path: Path) -> int:
    size = 0
    for file in path.rglob("*"):
        if file.is_file():
            size += file.stat().st_size
    return size


def run(
    tool: str,
    operation: str,
    source: str,
    target: str,
    env_file: Path | None,
    profile_folder: Path | None = None,
) -> dict[str, Any]:
    is_local = "://" not in target
    if is_local and Path(target).exists():
        shutil.rmtree(target)
    environ = tool_environ(tool, env_file)
    profile = None
    if profile_folder is not None and tool == "xarray-sentinel":
        environ["DASK_SCHEDULER"] = "synchronous"
        scheme = source.rpartition("://")[0] or "file"
        profile = profile_folder / f"{operation}-{scheme}-{Path(target).stem}"
    args = [
        arg.format(source=source, target=target) for arg in OPERATIONS[operation][tool]
    ]
    result = measure(tool_command(tool, *args, profile=profile), environ)
    if is_local and Path(target).exists():
        result["output_size"] = directory_size(Path(target))
    if profile is not None:
        result["profile"] = f"{profile}.pyisession"
    return result


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        config = tomllib.load(file)
    for operation in config["operations"]:
        if operation not in OPERATIONS:
            raise ValueError(
                f"unknown operation {operation!r}, use: {list(OPERATIONS)}"
            )
    for tool in config.setdefault("tools", TOOLS):
        if tool not in TOOLS:
            raise ValueError(f"unknown tool {tool!r}, use: {TOOLS}")
    # relative paths are relative to the configuration file
    config["products"] = [
        product if "://" in product else str(path.parent / product)
        for product in config["products"]
    ]
    target = config.get("target", "output")
    if "://" not in target:
        config["target"] = str(path.parent / target)
    if "env_file" in config:
        config["env_file"] = path.parent / config["env_file"]
    config.setdefault("repeat", 1)
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", type=Path, help="TOML configuration file")
    parser.add_argument("--label", default=socket.gethostname(), help="setup name")
    parser.add_argument("--profile", type=Path, help="folder of the profiles")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    if args.profile is not None:
        args.profile.mkdir(parents=True, exist_ok=True)
    env_file = config.get("env_file")

    versions = {}
    for tool in config["tools"]:
        command = tool_command(tool, "--version")
        output = subprocess.run(
            command, capture_output=True, env=tool_environ(tool, env_file)
        )
        versions[tool] = output.stdout.decode().strip()

    results = BENCHMARKS / "results" / f"{args.label}.jsonl"
    results.parent.mkdir(exist_ok=True)
    for repeat in range(config["repeat"]):
        for source in config["products"]:
            name = Path(source.rstrip("/")).name.removesuffix(".SAFE")
            for operation in config["operations"]:
                for tool in config["tools"]:
                    if tool not in OPERATIONS[operation]:
                        continue
                    target = (
                        f"{config['target'].rstrip('/')}/{operation}/{tool}/{name}.zarr"
                    )
                    result = run(
                        tool, operation, source, target, env_file, args.profile
                    )
                    record = {
                        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                        "label": args.label,
                        "tool": tool,
                        "version": versions[tool],
                        "operation": operation,
                        "source": source,
                        "target": target,
                        "repeat": repeat,
                        **result,
                        "environ": recorded_environ(tool_environ(tool, env_file)),
                        "host": host_info(),
                    }
                    with results.open("a") as file:
                        file.write(json.dumps(record) + "\n")
                    status = "failed" if result["returncode"] else "ok"
                    print(
                        f"{operation} {tool} {name} #{repeat}: "
                        f"{result['wall_time']:.1f}s {status}",
                        flush=True,
                    )


if __name__ == "__main__":
    main()
