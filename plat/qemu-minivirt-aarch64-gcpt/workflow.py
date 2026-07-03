from __future__ import annotations

from pathlib import Path

from arch.aarch64.firmware import gcpt
from lib.common import BuildError, load_symbol, write_text
from lib.context import BuildContext


def _base_symbol(ctx: BuildContext, name: str):
    return load_symbol(ctx.root_dir / "plat" / "qemu-minivirt-aarch64" / "workflow.py", name)


def doctor(ctx: BuildContext) -> list[Path]:
    return _base_symbol(ctx, "doctor")(ctx)


def doctor_tools(ctx: BuildContext) -> list[str]:
    return _base_symbol(ctx, "doctor_tools")(ctx)


def build_dtb(ctx: BuildContext) -> Path:
    return _base_symbol(ctx, "build_dtb")(ctx)


def build_kernel(ctx: BuildContext) -> Path:
    return _base_symbol(ctx, "build_kernel")(ctx)


def _qemu_run_script(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "run-qemu.sh"


def _write_qemu_run_script(ctx: BuildContext, image: Path) -> Path:
    script = _qemu_run_script(ctx)
    qemu = str(ctx.default("qemu_binary", "qemu-system-aarch64"))
    machine = str(ctx.default("qemu_machine", "mini-virt"))
    cpu = str(ctx.default("qemu_cpu", "cortex-a57"))
    memory = str(ctx.default("qemu_memory", "1024M"))
    content = f"""#!/usr/bin/env bash
set -euo pipefail

QEMU_SYSTEM_AARCH64="${{QEMU_SYSTEM_AARCH64:-{qemu}}}"

"$QEMU_SYSTEM_AARCH64" \\
  -machine {machine} \\
  -cpu {cpu} \\
  -smp {ctx.harts()} \\
  -m {memory} \\
  -nographic \\
  -kernel "{image}"
"""
    write_text(script, content, ctx.args.dry_run)
    if not ctx.args.dry_run:
        script.chmod(0o755)
    return script


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware != "gcpt":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    if ctx.arch != "aarch64":
        raise BuildError("AArch64 GCPT firmware flow is only enabled for AArch64")

    image = gcpt.build(ctx)
    _write_qemu_run_script(ctx, image)
    return image


def final_payload(ctx: BuildContext) -> Path:
    if ctx.firmware == "gcpt":
        return gcpt.gcpt_bin(ctx)
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
