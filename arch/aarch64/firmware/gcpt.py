from __future__ import annotations

import shutil
from pathlib import Path

from arch.aarch64.firmware import payload as aarch64_payload
from lib.common import BuildError, log, run, write_text
from lib.context import BuildContext
from lib.resources import ensure_resource, remove_path


def _gcpt_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("gcpt", {}))


def _to_int(value: str | int | None, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, int):
        return value
    return int(value, 0)


def build_dir(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "gcpt"


def gcpt_elf(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "gcpt.elf"


def gcpt_bin(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "gcpt.bin"


def _work_dir(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "source"


def _metadata_path(ctx: BuildContext) -> Path:
    return build_dir(ctx) / "layout.txt"


def _link_address(ctx: BuildContext) -> int:
    return _to_int(_gcpt_config(ctx).get("link_address"), 0x40000000)


def _payload_position(ctx: BuildContext) -> int:
    return _to_int(_gcpt_config(ctx).get("payload_position"), 0x40100000)


def _prepare_source(ctx: BuildContext, source: Path) -> Path:
    gcpt_dir = build_dir(ctx)
    work_dir = _work_dir(ctx)
    log(f"install AArch64 LibCheckpoint source {source} -> {work_dir}")
    if ctx.args.dry_run:
        return work_dir

    remove_path(gcpt_dir)
    work_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        work_dir,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "build"),
    )
    return work_dir


def build(ctx: BuildContext) -> Path:
    source = ensure_resource(ctx, "libcheckpoint-for-aarch64")
    payload = aarch64_payload.build(ctx)

    if not payload.exists() and not ctx.args.dry_run:
        raise BuildError(f"GCPT payload is missing: {payload}. Run payload build first.")

    link_address = _link_address(ctx)
    payload_position = _payload_position(ctx)
    if payload_position <= link_address:
        raise BuildError(
            f"gcpt.payload_position must be above link_address: "
            f"0x{payload_position:x} <= 0x{link_address:x}"
        )

    work_dir = _prepare_source(ctx, source)
    run(
        [
            "make",
            "-C",
            str(work_dir),
            f"O={build_dir(ctx)}",
            f"BINARY={gcpt_bin(ctx)}",
            f"ELF={gcpt_elf(ctx)}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            f"PAYLOAD={payload.resolve()}",
            f"LINK_ADDRESS=0x{link_address:x}",
            f"PAYLOAD_POSITION=0x{payload_position:x}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=ctx.build_env(),
        dry_run=ctx.args.dry_run,
    )

    image = gcpt_bin(ctx)
    if not ctx.args.dry_run and not image.exists():
        raise BuildError(f"Expected AArch64 GCPT image does not exist: {image}")

    metadata = "\n".join(
        [
            f"link_address=0x{link_address:x}",
            f"payload_position=0x{payload_position:x}",
            f"payload={payload}",
            f"gcpt={image}",
            "",
        ]
    )
    write_text(_metadata_path(ctx), metadata, ctx.args.dry_run)
    return image
