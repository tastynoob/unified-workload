from __future__ import annotations

from pathlib import Path

from lib.common import BuildError, run
from lib.context import BuildContext
from lib.resources import ensure_resource


def build(ctx: BuildContext) -> Path:
    opensbi = ensure_resource(ctx, "opensbi")
    image = ctx.linux_image()
    dtb = ctx.dtb_path()
    if not image.exists():
        raise BuildError(f"Linux Image is missing: {image}. Run build-kernel first.")
    if not dtb.exists():
        raise BuildError(f"DTB is missing: {dtb}. Run build-dtb first.")

    build_dir = ctx.profile_build_dir() / "opensbi"
    run(
        [
            "make",
            "-C",
            str(opensbi),
            f"O={build_dir}",
            f"PLATFORM={ctx.opensbi_platform}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            "FW_PAYLOAD=y",
            f"FW_PAYLOAD_PATH={image.resolve()}",
            f"FW_FDT_PATH={dtb.resolve()}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=ctx.build_env(),
        dry_run=ctx.args.dry_run,
    )

    payload = ctx.fw_payload_bin()
    if not ctx.args.dry_run and not payload.exists():
        raise BuildError(f"Expected OpenSBI payload does not exist: {payload}")
    return payload
