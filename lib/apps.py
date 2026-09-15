from __future__ import annotations

import json
from pathlib import Path

from lib.common import BuildError, load_module, run, write_text
from lib.context import BuildContext
from lib.toolchain import cross_gcc


def discover_c_sources(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".c" else []
    return sorted(path.glob("*.c"))


def _workload_workflow(ctx: BuildContext):
    path = ctx.app_dir() / "workflow.py"
    return load_module(path) if path.is_file() else None


def workload_doctor(ctx: BuildContext) -> None:
    workflow = _workload_workflow(ctx)
    doctor = getattr(workflow, "doctor", None) if workflow else None
    if doctor is not None:
        doctor(ctx)


def validate_workload(ctx: BuildContext) -> None:
    workflow = _workload_workflow(ctx)
    validate = getattr(workflow, "validate_options", None) if workflow else None
    if validate is not None:
        validate(ctx)


def build_workload(ctx: BuildContext) -> Path:
    workflow = _workload_workflow(ctx)
    custom_build = getattr(workflow, "build_workload", None) if workflow else None
    if custom_build is not None:
        return custom_build(ctx)

    source_dir = ctx.app_dir()
    sources = discover_c_sources(source_dir)

    binary = ctx.workload_binary()
    if not ctx.args.dry_run:
        binary.parent.mkdir(parents=True, exist_ok=True)

    makefile = source_dir / "Makefile" if source_dir.is_dir() else None
    if makefile is not None and makefile.exists():
        make_env = ctx.build_env()
        make_env["UNIFIED_WORKLOAD_HOME"] = str(ctx.root_dir)
        make_env["UNIFIED_WORKLOAD_OPTIONS"] = json.dumps(
            ctx.workload_options, sort_keys=True, separators=(",", ":")
        )
        configure_build_env = (
            getattr(workflow, "configure_build_env", None) if workflow else None
        )
        if configure_build_env is not None:
            configure_build_env(ctx, make_env)
        run(
            [
                "make",
                "-C",
                str(source_dir),
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
    initramfs_entries = (
        getattr(workflow, "initramfs_entries", None) if workflow else None
    )
    if initramfs_entries is not None:
        extra_entries = initramfs_entries(ctx)
        if extra_entries:
            manifest += "\n" + extra_entries + "\n"
    write_text(initramfs, manifest, ctx.args.dry_run)
    return initramfs
