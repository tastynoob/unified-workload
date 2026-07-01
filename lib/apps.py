from __future__ import annotations

from pathlib import Path

from lib.common import BuildError, run, write_text
from lib.context import BuildContext
from lib.toolchain import cross_gcc


def discover_c_sources(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".c" else []
    return sorted(path.glob("*.c"))


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
        run(
            [
                "make",
                "-C",
                str(source_dir),
                f"CROSS_COMPILE={ctx.args.cross_compile}",
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
    write_text(initramfs, manifest, ctx.args.dry_run)
    return initramfs
