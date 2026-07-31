from __future__ import annotations

import struct
from pathlib import Path

from lib.common import BuildError, log, run, write_text
from lib.context import BuildContext


def _payload_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("payload", {}))


def _to_int(value: str | int | None, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, int):
        return value
    return int(value, 0)


def _align_up(value: int, align: int) -> int:
    return (value + align - 1) & ~(align - 1)


def payload_base(ctx: BuildContext) -> int:
    return _to_int(_payload_config(ctx).get("base"), 0x60000000)


def payload_bin(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "aarch64-payload.bin"


def _stub_asm(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "boot-stub.S"


def _stub_obj(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "boot-stub.o"


def _stub_elf(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "boot-stub.elf"


def _stub_bin(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "boot-stub.bin"


def _metadata_path(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "payload" / "layout.txt"


def _cross_tool(ctx: BuildContext, name: str) -> str:
    if not ctx.args.cross_compile:
        raise BuildError("AArch64 payload build requires --cross-compile")
    return f"{ctx.args.cross_compile}{name}"


def _arm64_image_size(kernel: Path) -> int:
    data = kernel.read_bytes()[:0x40]
    if len(data) < 0x40:
        raise BuildError(f"Linux Image is too small: {kernel}")

    magic = struct.unpack_from("<I", data, 0x38)[0]
    if magic != 0x644D5241:
        raise BuildError(f"Linux Image has an invalid arm64 header magic: {kernel}")

    image_size = struct.unpack_from("<Q", data, 0x10)[0]
    return int(image_size)


def _stub_source(kernel_addr: int, dtb_addr: int) -> str:
    return f"""\
.section .text.boot, "ax"
.global _start

_start:
    ldr x0, 1f
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    ldr x4, 2f
    mrs x5, CurrentEL
    lsr x5, x5, #2
    cmp x5, #3
    b.eq enter_from_el3
    cmp x5, #2
    b.eq enter_from_el2
    br x4

enter_from_el3:
    mov x6, #0x501
    movk x6, #0x3, lsl #16
    mov x7, xzr
    mov x9, xzr

    mrs x8, id_aa64pfr0_el1
    ubfx x10, x8, #32, #4
    cbz x10, no_el3_sve
    orr x7, x7, #(1 << 8)
    orr x9, x9, #1
no_el3_sve:

    mrs x8, id_aa64pfr1_el1
    ubfx x10, x8, #8, #4
    cmp x10, #2
    b.lo no_el3_mte
    orr x6, x6, #(1 << 26)
no_el3_mte:
    ubfx x10, x8, #24, #4
    cbz x10, no_el3_sme
    orr x6, x6, #(1 << 41)
    orr x7, x7, #(1 << 12)
    orr x9, x9, #2
no_el3_sme:

    mrs x8, id_aa64mmfr0_el1
    ubfx x10, x8, #56, #4
    cbz x10, no_el3_fgt
    orr x6, x6, #(1 << 27)
no_el3_fgt:

    mrs x8, id_aa64mmfr1_el1
    ubfx x10, x8, #40, #4
    cbz x10, no_el3_hcx
    orr x6, x6, #(1 << 38)
no_el3_hcx:

    mrs x8, S3_0_C0_C7_3
    ubfx x10, x8, #0, #4
    cbz x10, no_el3_tcr2
    orr x6, x6, #(1 << 43)
no_el3_tcr2:
    ubfx x10, x8, #8, #4
    cbz x10, no_el3_s1pie
    orr x6, x6, #(1 << 45)
no_el3_s1pie:

    msr scr_el3, x6
    msr cptr_el3, x7
    isb

    tbz x9, #0, done_el3_sve
    mov x8, #0xf
    msr S3_6_C1_C2_0, x8
done_el3_sve:
    tbz x9, #1, done_el3_sme
    mov x10, #0xf
    mrs x8, S3_0_C0_C4_5
    tbz x8, #63, no_el3_sme_fa64
    orr x10, x10, #(1 << 31)
no_el3_sme_fa64:
    ubfx x8, x8, #56, #4
    cbz x8, no_el3_sme2
    orr x10, x10, #(1 << 30)
no_el3_sme2:
    msr S3_6_C1_C2_6, x10
done_el3_sme:
    mov x6, #(1 << 31)
    msr hcr_el2, x6
    mov x6, #0x3
    msr cnthctl_el2, x6
    msr cntvoff_el2, xzr
    msr cptr_el2, xzr
    msr elr_el3, x4
    mov x6, #0x3c9
    msr spsr_el3, x6
    isb
    eret

enter_from_el2:
    mov x6, #(1 << 31)
    msr hcr_el2, x6
    mov x6, #0x3
    msr cnthctl_el2, x6
    msr cntvoff_el2, xzr
    msr cptr_el2, xzr
    isb
    br x4

.align 3
1:
    .quad 0x{dtb_addr:x}
2:
    .quad 0x{kernel_addr:x}
"""


def _build_stub(ctx: BuildContext, base: int, kernel_addr: int, dtb_addr: int) -> Path:
    asm = _stub_asm(ctx)
    obj = _stub_obj(ctx)
    elf = _stub_elf(ctx)
    binary = _stub_bin(ctx)

    write_text(asm, _stub_source(kernel_addr, dtb_addr), ctx.args.dry_run)
    run(
        [
            _cross_tool(ctx, "gcc"),
            "-x",
            "assembler-with-cpp",
            "-c",
            "-o",
            str(obj),
            str(asm),
        ],
        dry_run=ctx.args.dry_run,
    )
    run(
        [
            _cross_tool(ctx, "ld"),
            "-Ttext",
            f"0x{base:x}",
            "-o",
            str(elf),
            str(obj),
        ],
        dry_run=ctx.args.dry_run,
    )
    run(
        [
            _cross_tool(ctx, "objcopy"),
            "-O",
            "binary",
            str(elf),
            str(binary),
        ],
        dry_run=ctx.args.dry_run,
    )
    return binary


def _write_payload(
    ctx: BuildContext,
    stub: Path,
    kernel: Path,
    dtb: Path,
    kernel_offset: int,
    dtb_offset: int,
    kernel_runtime_size: int,
) -> Path:
    image = payload_bin(ctx)
    log(f"pack AArch64 payload {image}")
    if ctx.args.dry_run:
        return image

    stub_data = stub.read_bytes()
    kernel_data = kernel.read_bytes()
    dtb_data = dtb.read_bytes()

    if len(stub_data) > kernel_offset:
        raise BuildError(
            f"AArch64 boot stub is too large: {len(stub_data)} > kernel offset {kernel_offset}"
        )
    kernel_end = kernel_offset + max(len(kernel_data), kernel_runtime_size)
    if kernel_end > dtb_offset:
        raise BuildError(f"Linux Image overlaps DTB: kernel_end=0x{kernel_end:x}, dtb=0x{dtb_offset:x}")

    image.parent.mkdir(parents=True, exist_ok=True)
    with image.open("wb") as out:
        out.write(stub_data)
        out.write(b"\0" * (kernel_offset - out.tell()))
        out.write(kernel_data)
        out.write(b"\0" * (dtb_offset - out.tell()))
        out.write(dtb_data)
    return image


def build(ctx: BuildContext) -> Path:
    kernel = ctx.linux_image()
    dtb = ctx.dtb_path()
    if not ctx.args.dry_run:
        if not kernel.exists():
            raise BuildError(f"Linux Image is missing: {kernel}. Run build-kernel first.")
        if not dtb.exists():
            raise BuildError(f"DTB is missing: {dtb}. Run build-dtb first.")

    cfg = _payload_config(ctx)
    base = payload_base(ctx)
    kernel_offset = _to_int(cfg.get("kernel_offset"), 0x200000)
    dtb_align = _to_int(cfg.get("dtb_align"), 0x1000)
    dtb_offset_value = cfg.get("dtb_offset")
    kernel_runtime_size = 0 if ctx.args.dry_run else max(kernel.stat().st_size, _arm64_image_size(kernel))
    if dtb_offset_value is None:
        dtb_offset = _align_up(kernel_offset + kernel_runtime_size, dtb_align)
    else:
        dtb_offset = _to_int(dtb_offset_value, 0)

    kernel_addr = base + kernel_offset
    dtb_addr = base + dtb_offset
    stub = _build_stub(ctx, base, kernel_addr, dtb_addr)
    image = _write_payload(ctx, stub, kernel, dtb, kernel_offset, dtb_offset, kernel_runtime_size)

    metadata = "\n".join(
        [
            f"payload_base=0x{base:x}",
            f"kernel_offset=0x{kernel_offset:x}",
            f"kernel_addr=0x{kernel_addr:x}",
            f"dtb_offset=0x{dtb_offset:x}",
            f"dtb_addr=0x{dtb_addr:x}",
            f"payload={image}",
            "",
        ]
    )
    write_text(_metadata_path(ctx), metadata, ctx.args.dry_run)
    return image
