from __future__ import annotations

from pathlib import Path

from lib.common import BuildError, run
from lib.context import BuildContext
from lib.resources import ensure_resource


def _opensbi_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("opensbi", {}))


def build(ctx: BuildContext) -> Path:
    opensbi = ensure_resource(ctx, "opensbi")
    image = ctx.linux_image()
    dtb = ctx.dtb_path()
    if not image.exists() and not ctx.args.dry_run:
        raise BuildError(f"Linux Image is missing: {image}. Run build-kernel first.")
    if not dtb.exists() and not ctx.args.dry_run:
        raise BuildError(f"DTB is missing: {dtb}. Run build-dtb first.")

    build_dir = ctx.profile_build_dir() / "opensbi"
    cmd = [
        "make",
        "-C",
        str(opensbi),
        f"O={build_dir}",
        f"PLATFORM={ctx.opensbi_platform}",
        f"CROSS_COMPILE={ctx.args.cross_compile}",
        "FW_PAYLOAD=y",
        f"FW_PAYLOAD_PATH={image.resolve()}",
        f"FW_FDT_PATH={dtb.resolve()}",
    ]
    opensbi_cfg = _opensbi_config(ctx)
    if opensbi_cfg.get("fw_payload_offset") is not None:
        cmd.append(f"FW_PAYLOAD_OFFSET={opensbi_cfg['fw_payload_offset']}")
    if opensbi_cfg.get("fw_payload_align") is not None:
        cmd.append(f"FW_PAYLOAD_ALIGN={opensbi_cfg['fw_payload_align']}")
    if opensbi_cfg.get("fw_text_start") is not None:
        cmd.append(f"FW_TEXT_START={opensbi_cfg['fw_text_start']}")
    cmd.extend(["-j", str(ctx.args.jobs)])

    run(
        cmd,
        env=ctx.build_env(),
        dry_run=ctx.args.dry_run,
    )

    payload = ctx.fw_payload_bin()
    if not ctx.args.dry_run and not payload.exists():
        raise BuildError(f"Expected OpenSBI payload does not exist: {payload}")
    return payload
