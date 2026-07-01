from __future__ import annotations

from pathlib import Path

from arch.aarch64.firmware import tfa
from lib.common import BuildError, log, write_text
from lib.context import BuildContext
from lib.linux import build_kernel as build_linux_kernel


def doctor(ctx: BuildContext) -> list[Path]:
    required = [ctx.linux_defconfig()]
    return [path for path in required if not path.exists()]


def doctor_tools(ctx: BuildContext) -> list[str]:
    return ["qemu-system-aarch64"]


def build_dtb(ctx: BuildContext) -> Path:
    marker = ctx.profile_build_dir() / "dtb" / "qemu-runtime-dtb.txt"
    log("qemu-virt-aarch64 uses the QEMU-generated runtime DTB")
    write_text(marker, "QEMU virt generates and passes the DTB at runtime.\n", ctx.args.dry_run)
    return marker


def build_kernel(ctx: BuildContext) -> Path:
    return build_linux_kernel(ctx, ctx.linux_defconfig())


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware != "tfa":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    return tfa.build(ctx)


def final_payload(ctx: BuildContext) -> Path:
    if ctx.firmware == "tfa":
        return tfa.flash_bin(ctx)
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
