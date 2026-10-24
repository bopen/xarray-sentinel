"""Benchmark the SAFE to EOPF Zarr conversion of the xarray-sentinel and eopf CLIs.

Run with any Python 3.11+, the tools run in their own uv environments:

    python benchmarks/run.py benchmarks/config.toml

The products, the operations and the tools are selected in the configuration file.
Each run appends a JSON record to ``benchmarks/results/<label>.jsonl``.
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
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

BENCHMARKS = Path(__file__).resolve().parent
TOOLS = ["xarray-sentinel", "eopf"]

# the CLI arguments of each tool supporting the operation
OPERATIONS = {
    "convert": {
        "xarray-sentinel": ["convert", "{source}", "{target}"],
        "eopf": ["convert", "{source}", "{target}", "--use-dask-config"],
    },
    "convert-staged": {
        "eopf": [
            "convert",
            "{source}",
            "{target}",
            "--use-dask-config",
            "--stage-source",
        ],
    },
}

EOPF_TOML = """\
[logging]
level = "INFO"
dask_level = "WARNING"

[dask_context]
cluster_type = "local"

[dask_context.cluster_config]
n_workers = {n_workers}
threads_per_worker = {threads_per_worker}
processes = true
"""


def tool_command(tool: str, *args: str, env_file: Path | None = None) -> list[str]:
    uv_run = ["uv", "run", "--frozen"]
    if env_file is not None:
        uv_run += ["--env-file", str(env_file)]
    if tool == "xarray-sentinel":
        uv_run += ["--extra", "lab", "--project", str(BENCHMARKS.parent)]
    else:
        uv_run += ["--project", str(BENCHMARKS / "eopf")]
    return [*uv_run, tool, *args]


def host_info() -> dict[str, Any]:
    memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory": memory,
    }


def dask_environ() -> dict[str, str]:
    environ = {}
    for key, value in os.environ.items():
        if key.startswith(("DASK_", "EOPF_")):
            environ[key] = value
    return environ


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
    config_folder: str,
    env_file: Path | None,
) -> dict[str, Any]:
    is_local = "://" not in target
    if is_local and Path(target).exists():
        shutil.rmtree(target)
    env = dict(os.environ)
    if tool == "eopf":
        env["EOPF_CONFIGURATION_FOLDER"] = config_folder
    args = [
        arg.format(source=source, target=target) for arg in OPERATIONS[operation][tool]
    ]
    result = measure(tool_command(tool, *args, env_file=env_file), env)
    if is_local and Path(target).exists():
        result["output_size"] = directory_size(Path(target))
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
    target = config.get("target", "output")
    if "://" not in target:
        config["target"] = str(path.parent / target)
    if "env_file" in config:
        config["env_file"] = path.parent / config["env_file"]
    config.setdefault("repeat", 1)
    config.setdefault("eopf", {})
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", type=Path, help="TOML configuration file")
    parser.add_argument("--label", default=socket.gethostname(), help="setup name")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    env_file = config.get("env_file")
    n_workers = config["eopf"].get("n_workers", 2)
    threads_per_worker = config["eopf"].get("threads_per_worker", 2)

    versions = {}
    for tool in config["tools"]:
        command = tool_command(tool, "--version", env_file=env_file)
        output = subprocess.run(command, capture_output=True)
        versions[tool] = output.stdout.decode().strip()

    results = BENCHMARKS / "results" / f"{args.label}.jsonl"
    results.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as config_folder:
        eopf_toml = EOPF_TOML.format(
            n_workers=n_workers, threads_per_worker=threads_per_worker
        )
        (Path(config_folder) / "eopf.toml").write_text(eopf_toml)
        for repeat in range(config["repeat"]):
            for source in config["products"]:
                name = Path(source.rstrip("/")).name.removesuffix(".SAFE")
                for operation in config["operations"]:
                    for tool in config["tools"]:
                        if tool not in OPERATIONS[operation]:
                            continue
                        target = f"{config['target'].rstrip('/')}/{operation}/{tool}/{name}.zarr"
                        result = run(
                            tool, operation, source, target, config_folder, env_file
                        )
                        record = {
                            "timestamp": datetime.datetime.now(
                                datetime.UTC
                            ).isoformat(),
                            "label": args.label,
                            "tool": tool,
                            "version": versions[tool],
                            "operation": operation,
                            "source": source,
                            "target": target,
                            "n_workers": n_workers,
                            "threads_per_worker": threads_per_worker,
                            "repeat": repeat,
                            **result,
                            "environ": dask_environ(),
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
