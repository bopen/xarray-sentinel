"""Benchmark the SAFE to EOPF Zarr conversion of the xarray-sentinel and eopf CLIs.

Run with any Python 3.11+, the tools run in their own uv environments:

    python benchmarks/run.py SOURCE [SOURCE ...] --target DIR_OR_URL

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
from pathlib import Path
from typing import Any

BENCHMARKS = Path(__file__).resolve().parent
TOOLS = ["xarray-sentinel", "eopf"]

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


def tool_command(tool: str, *args: str) -> list[str]:
    if tool == "xarray-sentinel":
        uv_run = ["uv", "run", "--frozen", "--extra", "lab"]
        return [*uv_run, "--project", str(BENCHMARKS.parent), tool, *args]
    return ["uv", "run", "--frozen", "--project", str(BENCHMARKS / "eopf"), tool, *args]


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
    source: str,
    target: str,
    config_folder: str,
) -> dict[str, Any]:
    is_local = "://" not in target
    if is_local and Path(target).exists():
        shutil.rmtree(target)
    env = dict(os.environ)
    if tool == "xarray-sentinel":
        command = tool_command(tool, "convert", source, target)
    else:
        env["EOPF_CONFIGURATION_FOLDER"] = config_folder
        command = tool_command(tool, "convert", source, target, "--use-dask-config")
    result = measure(command, env)
    if is_local and Path(target).exists():
        result["output_size"] = directory_size(Path(target))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="+", help="SAFE products, paths or URLs")
    parser.add_argument("--target", required=True, help="output directory or URL")
    parser.add_argument("--tool", action="append", choices=TOOLS)
    parser.add_argument("--n-workers", type=int, default=2, help="eopf only")
    parser.add_argument("--threads-per-worker", type=int, default=2, help="eopf only")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--label", default=socket.gethostname(), help="setup name")
    args = parser.parse_args()
    tools = args.tool or TOOLS

    versions = {}
    for tool in tools:
        output = subprocess.run(tool_command(tool, "--version"), capture_output=True)
        versions[tool] = output.stdout.decode().strip()

    results = BENCHMARKS / "results" / f"{args.label}.jsonl"
    results.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as config_folder:
        eopf_toml = EOPF_TOML.format(
            n_workers=args.n_workers, threads_per_worker=args.threads_per_worker
        )
        (Path(config_folder) / "eopf.toml").write_text(eopf_toml)
        for repeat in range(args.repeat):
            for source in args.sources:
                name = Path(source.rstrip("/")).name.removesuffix(".SAFE")
                for tool in tools:
                    target = f"{args.target.rstrip('/')}/{tool}/{name}.zarr"
                    result = run(tool, source, target, config_folder)
                    record = {
                        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                        "label": args.label,
                        "tool": tool,
                        "version": versions[tool],
                        "source": source,
                        "target": target,
                        "n_workers": args.n_workers,
                        "threads_per_worker": args.threads_per_worker,
                        "repeat": repeat,
                        **result,
                        "environ": dask_environ(),
                        "host": host_info(),
                    }
                    with results.open("a") as file:
                        file.write(json.dumps(record) + "\n")
                    status = "failed" if result["returncode"] else "ok"
                    print(
                        f"{tool} {name} #{repeat}: {result['wall_time']:.1f}s {status}"
                    )


if __name__ == "__main__":
    main()
