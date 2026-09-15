from __future__ import annotations

import os
from pathlib import Path

from lib.context import BuildContext


def configure_build_env(ctx: BuildContext, env: dict[str, str]) -> None:
    env["CROSS_COMPILE"] = os.environ.get(
        "SPEC_CROSS_COMPILE", ctx.args.cross_compile
    )


def initramfs_entries(ctx: BuildContext) -> str:
    benchmark = os.environ.get("SPEC_BENCHMARK", "401.bzip2")
    configured_work_dir = os.environ.get("SPEC_WORK_DIR")
    if configured_work_dir:
        input_dir = Path(configured_work_dir).expanduser().resolve() / "inputs"
    else:
        input_dir = (
            ctx.profile_build_dir()
            / "workload"
            / "obj"
            / "spec"
            / benchmark
            / "inputs"
        )
    if not input_dir.is_dir():
        return ""

    files = sorted(path for path in input_dir.rglob("*") if path.is_file())
    directories: set[Path] = set()
    for path in files:
        relative = path.relative_to(input_dir)
        directories.update(
            parent for parent in relative.parents if parent != Path(".")
        )
    directory_lines = [
        f"dir /{relative.as_posix()} 755 0 0"
        for relative in sorted(
            directories, key=lambda path: (len(path.parts), path.as_posix())
        )
    ]
    file_lines = [
        f"file /{path.relative_to(input_dir).as_posix()} {path.resolve()} 644 0 0"
        for path in files
    ]
    return "\n".join(directory_lines + file_lines)
