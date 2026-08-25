from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from lib.common import BuildError, log, run, write_text
from lib.context import BuildContext
from lib.resources import ensure_resource, resource_path, remove_path


def _to_int(value: str | int | None, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, int):
        return value
    return int(value, 0)


def _bare_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("bare", {}))


def _gcpt_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("gcpt", {}))


def _runtime_dir(ctx: BuildContext) -> Path:
    return ctx.platform_dir() / "runtime"


def _bare_build_dir(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "bare"


def _payload_elf(ctx: BuildContext) -> Path:
    return ctx.workload_binary()


def _payload_bin(ctx: BuildContext) -> Path:
    return _bare_build_dir(ctx) / "payload.bin"


def _gcpt_dir(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "gcpt"


def _gcpt_bin(ctx: BuildContext) -> Path:
    return _gcpt_dir(ctx) / "gcpt.bin"


def _cross_tool(ctx: BuildContext, tool: str) -> str:
    if not ctx.args.cross_compile:
        raise BuildError("AArch64 bare-metal build requires --cross-compile")
    return f"{ctx.args.cross_compile}{tool}"


def _tool_output(ctx: BuildContext, *args: str) -> str:
    try:
        result = subprocess.run(
            [_cross_tool(ctx, "gcc"), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def _toolchain_runtime(ctx: BuildContext) -> Path:
    target = _tool_output(ctx, "-dumpmachine")
    sysroot_text = _tool_output(ctx, "-print-sysroot")
    libc_text = _tool_output(ctx, "-print-file-name=libc.a")
    if target != "aarch64-none-elf":
        raise BuildError(
            "AArch64 bare-metal build requires an aarch64-none-elf toolchain"
        )
    if not sysroot_text or not libc_text or libc_text == "libc.a":
        raise BuildError("aarch64-none-elf toolchain does not provide newlib")

    include_dir = Path(sysroot_text).resolve() / "include"
    libc = Path(libc_text).resolve()
    if not (include_dir / "stdio.h").is_file() or not libc.is_file():
        raise BuildError("aarch64-none-elf toolchain has an incomplete newlib sysroot")
    log(f"use toolchain newlib from {libc.parent}")
    return libc.parent


def _write_linker_script(ctx: BuildContext) -> Path:
    cfg = _bare_config(ctx)
    payload_address = _to_int(cfg.get("payload_address"), 0x40200000)
    memory_end = _to_int(cfg.get("memory_end"), 0x80000000)
    stack_size = _to_int(cfg.get("stack_size"), 0x100000)
    if payload_address >= memory_end or stack_size >= memory_end - payload_address:
        raise BuildError("invalid AArch64 bare-metal memory layout")

    script = _bare_build_dir(ctx) / "linker.ld"
    content = f"""\
ENTRY(_start)

MEMORY
{{
    RAM (rwx) : ORIGIN = 0x{payload_address:x}, LENGTH = 0x{memory_end - payload_address:x}
}}

SECTIONS
{{
    . = ORIGIN(RAM);
    .text : {{
        KEEP(*(.text.boot))
        *(.text .text.*)
    }} > RAM

    .rodata : {{
        *(.rodata .rodata.*)
        *(.eh_frame .eh_frame.*)
    }} > RAM

    .preinit_array : {{
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    }} > RAM

    .init_array : {{
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*)))
        KEEP(*(.init_array))
        PROVIDE_HIDDEN(__init_array_end = .);
    }} > RAM

    .fini_array : {{
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.fini_array.*)))
        KEEP(*(.fini_array))
        PROVIDE_HIDDEN(__fini_array_end = .);
    }} > RAM

    .data : {{
        *(.data .data.*)
    }} > RAM

    .page_tables (NOLOAD) : ALIGN(4096) {{
        KEEP(*(.bss.page_tables))
    }} > RAM

    .bss (NOLOAD) : ALIGN(16) {{
        __bss_start = .;
        *(.bss .bss.* COMMON)
        . = ALIGN(16);
        __bss_end = .;
    }} > RAM

    . = ALIGN(16);
    __image_end = .;
    __heap_start = .;
    __stack_top = ORIGIN(RAM) + LENGTH(RAM);
    __stack_bottom = __stack_top - 0x{stack_size:x};
    __heap_end = __stack_bottom;

    /DISCARD/ : {{ *(.comment .note .note.*) }}
}}

ASSERT(__image_end <= __heap_end, "AArch64 bare-metal image overlaps stack")
"""
    write_text(script, content, ctx.args.dry_run)
    return script


def _build_runtime(ctx: BuildContext) -> tuple[Path, Path, Path]:
    build = _bare_build_dir(ctx) / "runtime"
    start_obj = build / "start.o"
    syscalls_obj = build / "syscalls.o"
    linker = _write_linker_script(ctx)
    if not ctx.args.dry_run:
        build.mkdir(parents=True, exist_ok=True)

    cfg = _bare_config(ctx)
    march = str(cfg.get("march", "armv9-a"))
    uart_base = _to_int(cfg.get("uart_base"), 0x09000000)
    common_flags = [
        f"-march={march}",
        "-ffreestanding",
        "-fno-pic",
        "-fno-pie",
        "-fno-stack-protector",
        "-ffunction-sections",
        "-fdata-sections",
        "-I",
        str(ctx.platform_dir() / "include"),
    ]
    run(
        [
            _cross_tool(ctx, "gcc"),
            *common_flags,
            "-x",
            "assembler-with-cpp",
            "-c",
            "-o",
            str(start_obj),
            str(_runtime_dir(ctx) / "start.S"),
        ],
        dry_run=ctx.args.dry_run,
    )
    run(
        [
            _cross_tool(ctx, "gcc"),
            *common_flags,
            "-O2",
            "-mcmodel=large",
            f"-DUART_BASE=0x{uart_base:x}UL",
            "-c",
            "-o",
            str(syscalls_obj),
            str(_runtime_dir(ctx) / "syscalls.c"),
        ],
        dry_run=ctx.args.dry_run,
    )
    return start_obj, syscalls_obj, linker


def build_workload(ctx: BuildContext) -> Path:
    if ctx.harts() != 1:
        raise BuildError("AArch64 bare-metal mini-virt supports exactly one CPU")

    lib_dir = _toolchain_runtime(ctx)
    start_obj, syscalls_obj, linker = _build_runtime(ctx)
    app_dir = ctx.app_dir()
    makefile = app_dir / "Makefile"
    if not makefile.exists():
        raise BuildError("AArch64 bare-metal workloads currently require an app Makefile")

    cfg = _bare_config(ctx)
    march = str(cfg.get("march", "armv9-a"))
    bare_cflags = [
        "-O3",
        f"-march={march}",
        "-ffreestanding",
        "-fno-pic",
        "-fno-pie",
        "-fno-stack-protector",
        "-ffunction-sections",
        "-fdata-sections",
    ]
    for flags in ctx.args.cflags:
        bare_cflags.extend(flags.split())
    bare_cxxflags = [flag for flag in bare_cflags if flag != "-ffreestanding"]

    bare_ldflags = [
        "-nostdlib",
        "-static",
        "-no-pie",
        f"-Wl,-T,{linker}",
        "-Wl,--gc-sections",
        "-Wl,--build-id=none",
    ]
    for flags in ctx.args.ldflags:
        bare_ldflags.extend(flags.split())

    env = os.environ.copy()
    env.update(
        {
            "ARCH": "aarch64",
            "BAREMETAL": "1",
            "BARE_CFLAGS": " ".join(bare_cflags),
            "BARE_CXXFLAGS": " ".join(bare_cxxflags),
            "BARE_LDFLAGS": " ".join(bare_ldflags),
            "EXTRA_OBJS": f"{start_obj} {syscalls_obj}",
            "LDLIBS": (
                f"-L{lib_dir} -Wl,--start-group -lc -lm -lgcc "
                "-Wl,--end-group"
            ),
            "UNIFIED_WORKLOAD_HOME": str(ctx.root_dir),
        }
    )
    run(
        [
            "make",
            "-C",
            str(app_dir),
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            f"PLATFORM={ctx.platform}",
            f"APP={_payload_elf(ctx)}",
            f"DST_DIR={ctx.profile_build_dir() / 'workload' / 'obj'}",
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )
    run(
        [
            _cross_tool(ctx, "objcopy"),
            "-O",
            "binary",
            str(_payload_elf(ctx)),
            str(_payload_bin(ctx)),
        ],
        dry_run=ctx.args.dry_run,
    )
    return _payload_bin(ctx)


def build_dtb(ctx: BuildContext) -> Path:
    log("AArch64 bare-metal platform does not build a DTB")
    return _payload_bin(ctx)


def build_kernel(ctx: BuildContext) -> Path:
    log("AArch64 bare-metal platform does not build Linux")
    return _payload_bin(ctx)


def _prepare_gcpt_source(ctx: BuildContext) -> Path:
    source = ensure_resource(ctx, "libcheckpoint-for-aarch64")
    work = _gcpt_dir(ctx) / "source"
    log(f"install AArch64 LibCheckpoint source {source} -> {work}")
    if ctx.args.dry_run:
        return work
    remove_path(_gcpt_dir(ctx))
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, work, symlinks=True, ignore=shutil.ignore_patterns(".git", "build"))
    return work


def _write_qemu_run_script(ctx: BuildContext, image: Path) -> Path:
    script = ctx.profile_build_dir() / "run-qemu.sh"
    qemu = str(ctx.default("qemu_binary", "qemu-system-aarch64"))
    machine = str(ctx.default("qemu_machine", "mini-virt"))
    cpu = str(ctx.default("qemu_cpu", "max"))
    memory = str(ctx.default("qemu_memory", "1024M"))
    content = f"""#!/usr/bin/env bash
set -euo pipefail

QEMU_SYSTEM_AARCH64="${{QEMU_SYSTEM_AARCH64:-{qemu}}}"

"$QEMU_SYSTEM_AARCH64" \\
  -machine {machine} \\
  -cpu {cpu} \\
  -smp 1 \\
  -m {memory} \\
  -nographic \\
  -kernel "{image}"
"""
    write_text(script, content, ctx.args.dry_run)
    if not ctx.args.dry_run:
        script.chmod(0o755)
    return script


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware != "bare-gcpt":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    if not _payload_bin(ctx).exists() and not ctx.args.dry_run:
        raise BuildError("bare payload is missing; run build-workload first")

    source = _prepare_gcpt_source(ctx)
    cfg = _gcpt_config(ctx)
    bare_cfg = _bare_config(ctx)
    link_address = _to_int(cfg.get("link_address"), 0x40000000)
    payload_position = _to_int(cfg.get("payload_position"), 0x40200000)
    uart_base = _to_int(bare_cfg.get("uart_base"), 0x13000000)
    run(
        [
            "make",
            "-C",
            str(source),
            f"O={_gcpt_dir(ctx)}",
            f"BINARY={_gcpt_bin(ctx)}",
            f"ELF={_gcpt_dir(ctx) / 'gcpt.elf'}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            f"PAYLOAD={_payload_bin(ctx).resolve()}",
            f"LINK_ADDRESS=0x{link_address:x}",
            f"PAYLOAD_POSITION=0x{payload_position:x}",
            f"UART_BASE=0x{uart_base:x}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=ctx.build_env(),
        dry_run=ctx.args.dry_run,
    )
    if not ctx.args.dry_run and not _gcpt_bin(ctx).exists():
        raise BuildError(f"expected GCPT image does not exist: {_gcpt_bin(ctx)}")
    _write_qemu_run_script(ctx, _gcpt_bin(ctx))
    return _gcpt_bin(ctx)


def final_payload(ctx: BuildContext) -> Path:
    return _gcpt_bin(ctx)


def doctor(ctx: BuildContext) -> list[Path]:
    required = [
        _runtime_dir(ctx) / "start.S",
        _runtime_dir(ctx) / "syscalls.c",
        resource_path(ctx, "libcheckpoint-for-aarch64"),
    ]
    return [path for path in required if not path.exists()]


def doctor_tools(ctx: BuildContext) -> list[str]:
    qemu = os.environ.get("QEMU_SYSTEM_AARCH64") or str(
        ctx.default("qemu_binary", "qemu-system-aarch64")
    )
    return [
        qemu,
        _cross_tool(ctx, "ar"),
        _cross_tool(ctx, "ld"),
        _cross_tool(ctx, "objcopy"),
        _cross_tool(ctx, "ranlib"),
    ]
