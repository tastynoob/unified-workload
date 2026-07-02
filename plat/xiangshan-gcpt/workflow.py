from __future__ import annotations

from pathlib import Path

from arch.riscv.firmware import gcpt, opensbi
from lib.common import BuildError, load_symbol
from lib.context import BuildContext


def _xiangshan_symbol(ctx: BuildContext, name: str):
    return load_symbol(ctx.root_dir / "plat" / "xiangshan" / "workflow.py", name)


def doctor(ctx: BuildContext) -> list[Path]:
    return _xiangshan_symbol(ctx, "doctor")(ctx)


def doctor_tools(ctx: BuildContext) -> list[str]:
    return _xiangshan_symbol(ctx, "doctor_tools")(ctx)


def build_dtb(ctx: BuildContext) -> Path:
    return _xiangshan_symbol(ctx, "build_dtb")(ctx)


def build_kernel(ctx: BuildContext) -> Path:
    return _xiangshan_symbol(ctx, "build_kernel")(ctx)


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware != "gcpt":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    if ctx.arch != "riscv":
        raise BuildError("GCPT firmware flow is only enabled for RISC-V")

    fw_payload = opensbi.build(ctx)
    return gcpt.build(ctx, fw_payload)


def final_payload(ctx: BuildContext) -> Path:
    if ctx.firmware == "gcpt":
        return gcpt.gcpt_bin(ctx)
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
