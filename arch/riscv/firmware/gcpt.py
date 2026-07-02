from __future__ import annotations

import shutil
from pathlib import Path

from lib.common import BuildError, log, run
from lib.context import BuildContext
from lib.resources import ensure_resource, remove_path


def _gcpt_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("gcpt", {}))


def build_dir(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "gcpt"


def gcpt_elf(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "gcpt"


def gcpt_bin(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "gcpt.bin"


def _work_dir(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "source"


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _link_address(ctx: BuildContext) -> str:
    return str(_gcpt_config(ctx).get("link_address", "0x80000000"))


def _patch_linker_script(ctx: BuildContext, work_dir: Path) -> None:
    link_address = _link_address(ctx)
    script = work_dir / "restore.lds"
    log(f"set LibCheckpoint link address {link_address}")
    if ctx.args.dry_run:
        return

    content = script.read_text(encoding="utf-8")
    old = "  . = ALIGN(4);\n  gcpt_begin = .;"
    new = f"  . = {link_address};\n  . = ALIGN(4);\n  gcpt_begin = .;"
    if old not in content:
        raise BuildError(f"Cannot patch LibCheckpoint linker script: {script}")
    script.write_text(content.replace(old, new, 1), encoding="utf-8")


def _prepare_source(ctx: BuildContext, source: Path) -> Path:
    gcpt_dir = build_dir(ctx)
    work_dir = _work_dir(ctx)
    log(f"install LibCheckpoint source {source} -> {work_dir}")
    if ctx.args.dry_run:
        return work_dir

    nanopb = source / "resource" / "nanopb" / "generator" / "nanopb_generator.py"
    if not nanopb.exists():
        raise BuildError(
            f"LibCheckpoint submodules are missing under {source}. "
            "Run fetch again, or run 'git submodule update --init --recursive' in that source tree."
        )

    remove_path(gcpt_dir)
    work_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        work_dir,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "build", "CONFIG.mk", "export_include"),
    )
    _patch_linker_script(ctx, work_dir)
    return work_dir


def _append_config_flags(ctx: BuildContext, work_dir: Path) -> None:
    cfg = _gcpt_config(ctx)
    cflags = ["-fno-stack-protector", *_as_list(cfg.get("cflags"))]
    ldflags = ["-no-pie", *_as_list(cfg.get("ldflags"))]

    log("configure LibCheckpoint freestanding compiler flags")
    if ctx.args.dry_run:
        return

    config = work_dir / "CONFIG.mk"
    with config.open("a", encoding="utf-8") as fh:
        fh.write("\n")
        if cflags:
            fh.write("CFLAGS += " + " ".join(cflags) + "\n")
        if ldflags:
            fh.write("LDFLAGS += " + " ".join(ldflags) + "\n")


def build(ctx: BuildContext, payload: Path) -> Path:
    source = ensure_resource(ctx, "libcheckpoint")
    if not payload.exists() and not ctx.args.dry_run:
        raise BuildError(f"GCPT payload is missing: {payload}. Run build-opensbi first.")

    cfg = _gcpt_config(ctx)
    work_dir = _prepare_source(ctx, source)

    configure = [
        "bash",
        "configure",
        f"--gcpt-payload={payload.resolve()}",
    ]
    if cfg.get("payload_position") is not None:
        configure.append(f"--gcpt-payload-position={cfg['payload_position']}")
    if cfg.get("mode") is not None:
        configure.append(f"--mode={cfg['mode']}")
    if cfg.get("display_cpu") is not None:
        configure.append(f"--display-cpu={cfg['display_cpu']}")
    if cfg.get("stop_cpu") is not None:
        configure.append(f"--stop-cpu={cfg['stop_cpu']}")

    run(configure, cwd=work_dir, env=ctx.build_env(), dry_run=ctx.args.dry_run)
    _append_config_flags(ctx, work_dir)
    run(
        [
            "make",
            "-C",
            str(work_dir),
            f"O={build_dir(ctx)}",
            f"BINARY={gcpt_elf(ctx)}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=ctx.build_env(),
        dry_run=ctx.args.dry_run,
    )

    image = gcpt_bin(ctx)
    if not ctx.args.dry_run and not image.exists():
        raise BuildError(f"Expected GCPT image does not exist: {image}")
    return image
