from __future__ import annotations

import os
from pathlib import Path

from lib.common import BuildError, run, write_text
from lib.context import BuildContext
from lib.toolchain import cross_gcc


def discover_c_sources(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".c" else []
    return sorted(path.glob("*.c"))


def _spec_cross_compile(ctx: BuildContext) -> str:
    if ctx.selected_workload() == "spec":
        return os.environ.get("SPEC_CROSS_COMPILE", ctx.args.cross_compile)
    return ctx.args.cross_compile


def _spec_input_manifest(ctx: BuildContext) -> str:
    if ctx.selected_workload() != "spec":
        return ""

    benchmark = os.environ.get("SPEC_BENCHMARK", "401.bzip2")
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

    lines = []
    for path in sorted(input_dir.rglob("*")):
        if path.is_file():
            relative = path.relative_to(input_dir).as_posix()
            lines.append(f"file /{relative} {path.resolve()} 644 0 0")
    return "\n".join(lines)


def build_workload(ctx: BuildContext) -> Path:
    source_dir = ctx.app_dir()
    sources = discover_c_sources(source_dir)

    binary = ctx.workload_binary()
    if not ctx.args.dry_run:
        binary.parent.mkdir(parents=True, exist_ok=True)

    makefile = source_dir / "Makefile" if source_dir.is_dir() else None
    if makefile is not None and makefile.exists():
        make_env = ctx.build_env()
        make_env["UNIFIED_WORKLOAD_HOME"] = str(ctx.root_dir)
        cross_compile = _spec_cross_compile(ctx)
        run(
            [
                "make",
                "-C",
                str(source_dir),
                f"CROSS_COMPILE={cross_compile}",
                f"PLATFORM={ctx.platform}",
                f"APP={binary}",
                f"DST_DIR={ctx.profile_build_dir() / 'workload' / 'obj'}",
            ],
            env=make_env,
            dry_run=ctx.args.dry_run,
        )
    else:
        if not sources:
            raise BuildError(f"No C sources or Makefile found for workload: {source_dir}")
        cmd = [
            cross_gcc(ctx.args.cross_compile),
            "-static",
            "-O2",
            "-Wall",
            "-Wextra",
            "-I",
            str(ctx.platform_dir() / "include"),
            "-I",
            str(ctx.root_dir / "include"),
            "-o",
            str(binary),
        ]
        for flag in ctx.args.cflags:
            cmd.extend(flag.split())
        cmd.extend(str(src) for src in sources)
        for flag in ctx.args.ldflags:
            cmd.extend(flag.split())
        run(cmd, env=ctx.build_env(), dry_run=ctx.args.dry_run)

    initramfs = ctx.initramfs_list()
    manifest = f"""dir /dev 755 0 0

nod /dev/console 644 0 0 c 5 1
nod /dev/null 644 0 0 c 1 3

file /init {binary.resolve()} 755 0 0
"""
    spec_inputs = _spec_input_manifest(ctx)
    if spec_inputs:
        manifest += "\n" + spec_inputs + "\n"
    write_text(initramfs, manifest, ctx.args.dry_run)
    return initramfs
