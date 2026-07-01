from __future__ import annotations

from pathlib import Path

from arch.riscv.firmware import opensbi
from lib.common import BuildError, load_symbol, write_text
from lib.context import BuildContext
from lib.linux import build_kernel as build_linux_kernel
from lib.common import run


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value, 0)


def _dtsgen_class(ctx: BuildContext):
    return load_symbol(ctx.dts_generator_path(), "DTSGen")


def doctor(ctx: BuildContext) -> list[Path]:
    required = [ctx.dts_generator_path(), ctx.linux_defconfig()]
    return [path for path in required if not path.exists()]


def generate_dts(ctx: BuildContext) -> str:
    dtsgen_cls = _dtsgen_class(ctx)
    isa_extensions = set(ctx.args.isa_extension)
    rva_profile = ctx.rva_profile()
    if rva_profile:
        isa_extensions.update(dtsgen_cls.get_isa_extensions_by_rva_profile(rva_profile))
    if not isa_extensions:
        isa_extensions.update(["i", "m", "a", "f", "d", "c"])
    isa_extensions = dtsgen_cls.sort_isa_extensions(list(isa_extensions))

    dtsgen = dtsgen_cls(
        nr_harts=ctx.harts(),
        nemu_sdhci_addr=_to_int(ctx.sd_addr()),
        isa_extensions=isa_extensions,
        bootargs=ctx.bootargs(),
        mmu_type=ctx.mmu_type(),
        timebase_freq=ctx.timebase_frequency(),
        memories=[(_to_int(ctx.memory_base()), _to_int(ctx.memory_size()))],
        uartlite_addr=_to_int(ctx.serial_addr()),
    )
    return dtsgen.gen_dts() + "\n"


def build_dtb(ctx: BuildContext) -> Path:
    dts = ctx.dts_path()
    dtb = ctx.dtb_path()
    write_text(dts, generate_dts(ctx), ctx.args.dry_run)
    run(["dtc", "-O", "dtb", "-o", str(dtb), str(dts)], dry_run=ctx.args.dry_run)
    return dtb


def build_kernel(ctx: BuildContext) -> Path:
    return build_linux_kernel(ctx, ctx.linux_defconfig())


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware != "opensbi":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    if ctx.arch != "riscv":
        raise BuildError("OpenSBI firmware is only supported for RISC-V")
    return opensbi.build(ctx)


def final_payload(ctx: BuildContext) -> Path:
    if ctx.firmware == "opensbi":
        return ctx.fw_payload_bin()
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
