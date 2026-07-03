from __future__ import annotations

import shutil
from pathlib import Path

from arch.aarch64.firmware import payload as aarch64_payload
from lib.common import BuildError, log, run, write_text
from lib.context import BuildContext
from lib.resources import ensure_resource


def _tfa_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("tfa", {}))


def _uboot_config(ctx: BuildContext) -> dict:
    return dict(ctx.platform_config.get("u_boot", {}))


def _bl33_mode(ctx: BuildContext) -> str:
    return str(_tfa_config(ctx).get("bl33", "u-boot"))


def _tfa_platform(ctx: BuildContext) -> str:
    return str(_tfa_config(ctx).get("platform", "qemu"))


def _tfa_build_type(ctx: BuildContext) -> str:
    return "debug" if bool(_tfa_config(ctx).get("debug", False)) else "release"


def _tfa_build_base(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "tfa"


def _tfa_build_dir(ctx: BuildContext) -> Path:
    return _tfa_build_base(ctx) / _tfa_platform(ctx) / _tfa_build_type(ctx)


def _u_boot_build_dir(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "u-boot"


def _u_boot_defconfig(ctx: BuildContext) -> str:
    return str(_uboot_config(ctx).get("defconfig", "qemu_arm64_defconfig"))


def _disable_u_boot_config(ctx: BuildContext) -> list[str]:
    disabled = list(_uboot_config(ctx).get("disable_config", []))
    if bool(_uboot_config(ctx).get("disable_efi_capsule_tool", False)):
        disabled.append("TOOLS_MKEFICAPSULE")
    return sorted(set(str(name) for name in disabled))


def u_boot_bin(ctx: BuildContext) -> Path:
    return _u_boot_build_dir(ctx) / "u-boot.bin"


def bl1_bin(ctx: BuildContext) -> Path:
    return _tfa_build_dir(ctx) / "bl1.bin"


def fip_bin(ctx: BuildContext) -> Path:
    return _tfa_build_dir(ctx) / "fip.bin"


def flash_bin(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "tfa" / "flash.bin"


def _tfa_build_stamp(ctx: BuildContext) -> Path:
    return _tfa_build_base(ctx) / ".unified-workload-build-key"


def qemu_run_script(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "run-qemu.sh"


def _qemu_initrd(ctx: BuildContext) -> Path:
    initrd = ctx.initramfs_cpio()
    if initrd.exists() or ctx.args.dry_run:
        return initrd

    generated = ctx.profile_build_dir() / "linux" / "usr" / "initramfs_data.cpio"
    if generated.exists():
        log(f"install initramfs cpio {generated} -> {initrd}")
        shutil.copy2(generated, initrd)
        return initrd

    raise BuildError(f"initramfs cpio is missing: {initrd}. Run build-kernel first.")


def build_u_boot(ctx: BuildContext) -> Path:
    source = ensure_resource(ctx, "u-boot")
    build_dir = _u_boot_build_dir(ctx)
    env = ctx.build_env()
    run(
        [
            "make",
            "-C",
            str(source),
            f"O={build_dir}",
            "ARCH=arm",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            _u_boot_defconfig(ctx),
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )
    for name in _disable_u_boot_config(ctx):
        run(
            [
                str(source / "scripts" / "config"),
                "--file",
                str(build_dir / ".config"),
                "--disable",
                name,
            ],
            env=env,
            dry_run=ctx.args.dry_run,
        )
    if _disable_u_boot_config(ctx):
        run(
            [
                "make",
                "-C",
                str(source),
                f"O={build_dir}",
                "ARCH=arm",
                f"CROSS_COMPILE={ctx.args.cross_compile}",
                "olddefconfig",
            ],
            env=env,
            dry_run=ctx.args.dry_run,
        )
    run(
        [
            "make",
            "-C",
            str(source),
            f"O={build_dir}",
            "ARCH=arm",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )

    image = u_boot_bin(ctx)
    if not ctx.args.dry_run and not image.exists():
        raise BuildError(f"Expected U-Boot image does not exist: {image}")
    return image


def _pack_flash(ctx: BuildContext, bl1: Path, fip: Path) -> Path:
    cfg = _tfa_config(ctx)
    fip_offset = int(str(cfg.get("fip_offset", "0x40000")), 0)
    flash_size = int(str(cfg.get("flash_size", "0x4000000")), 0)
    flash = flash_bin(ctx)

    log(f"pack TF-A flash {flash}")
    if ctx.args.dry_run:
        return flash

    if not bl1.exists():
        raise BuildError(f"TF-A BL1 does not exist: {bl1}")
    if not fip.exists():
        raise BuildError(f"TF-A FIP does not exist: {fip}")

    flash.parent.mkdir(parents=True, exist_ok=True)
    tmp = flash.with_name(f".{flash.name}.tmp")
    with tmp.open("wb") as out:
        out.truncate(flash_size)
        out.seek(0)
        out.write(bl1.read_bytes())
        out.seek(fip_offset)
        out.write(fip.read_bytes())
    tmp.rename(flash)
    return flash


def _tfa_build_key(ctx: BuildContext, bl33: Path, extra_args: list[str]) -> str:
    tfa_cfg = _tfa_config(ctx)
    parts = [
        f"platform={_tfa_platform(ctx)}",
        f"build_type={_tfa_build_type(ctx)}",
        f"debug={bool(tfa_cfg.get('debug', False))}",
        f"cross_compile={ctx.args.cross_compile}",
        f"bl33_mode={_bl33_mode(ctx)}",
        f"bl33={bl33.resolve()}",
        *extra_args,
    ]
    return "\n".join(parts) + "\n"


def _prepare_tfa_build(ctx: BuildContext, build_key: str) -> None:
    base = _tfa_build_base(ctx)
    stamp = _tfa_build_stamp(ctx)
    if ctx.args.dry_run:
        return
    if stamp.exists() and stamp.read_text(encoding="utf-8") == build_key:
        return
    if base.exists():
        log(f"clean stale TF-A build directory {base}")
        shutil.rmtree(base)


def _write_qemu_run_script(ctx: BuildContext, flash: Path) -> Path:
    script = qemu_run_script(ctx)
    qemu = str(ctx.default("qemu_binary", "qemu-system-aarch64"))
    memory = str(ctx.default("qemu_memory", "1024M"))
    cpu = str(ctx.default("qemu_cpu", "cortex-a57"))
    machine = str(ctx.default("qemu_machine", "virt,secure=on"))
    bootargs = ctx.bootargs()
    content = f"""#!/usr/bin/env bash
set -euo pipefail

QEMU_SYSTEM_AARCH64="${{QEMU_SYSTEM_AARCH64:-{qemu}}}"

"$QEMU_SYSTEM_AARCH64" \\
  -machine {machine} \\
  -cpu {cpu} \\
  -smp {ctx.harts()} \\
  -m {memory} \\
  -nographic \\
  -bios "{flash}"
"""
    if _bl33_mode(ctx) == "u-boot":
        image = ctx.linux_image()
        initrd = _qemu_initrd(ctx)
        content = f"""#!/usr/bin/env bash
set -euo pipefail

QEMU_SYSTEM_AARCH64="${{QEMU_SYSTEM_AARCH64:-{qemu}}}"

"$QEMU_SYSTEM_AARCH64" \\
  -machine {machine} \\
  -cpu {cpu} \\
  -smp {ctx.harts()} \\
  -m {memory} \\
  -nographic \\
  -bios "{flash}" \\
  -kernel "{image}" \\
  -initrd "{initrd}" \\
  -append "{bootargs}"
"""
    write_text(script, content, ctx.args.dry_run)
    if not ctx.args.dry_run:
        script.chmod(0o755)
    return script


def build(ctx: BuildContext) -> Path:
    if ctx.firmware != "tfa":
        raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
    if ctx.arch != "aarch64":
        raise BuildError("TF-A firmware flow is only enabled for AArch64")

    tfa = ensure_resource(ctx, "tfa")
    linux = ctx.linux_image()
    if not linux.exists() and not ctx.args.dry_run:
        raise BuildError(f"Linux Image is missing: {linux}. Run build-kernel first.")

    bl33_mode = _bl33_mode(ctx)
    if bl33_mode == "u-boot":
        bl33 = build_u_boot(ctx)
        tfa_extra_args: list[str] = []
    elif bl33_mode == "linux":
        bl33 = linux
        tfa_extra_args = ["ARM_LINUX_KERNEL_AS_BL33=1"]
    elif bl33_mode == "payload":
        bl33 = aarch64_payload.build(ctx)
        tfa_extra_args = []
    else:
        raise BuildError(f"Unsupported TF-A BL33 mode for platform {ctx.platform}: {bl33_mode}")

    tfa_build_key = _tfa_build_key(ctx, bl33, tfa_extra_args)
    _prepare_tfa_build(ctx, tfa_build_key)

    tfa_cfg = _tfa_config(ctx)
    env = ctx.build_env()
    cmd = [
        "make",
        "-C",
        str(tfa),
        f"BUILD_BASE={_tfa_build_base(ctx)}",
        f"PLAT={_tfa_platform(ctx)}",
        f"CROSS_COMPILE={ctx.args.cross_compile}",
        f"BL33={bl33.resolve()}",
        *tfa_extra_args,
        "all",
        "fip",
        "-j",
        str(ctx.args.jobs),
    ]
    if bool(tfa_cfg.get("debug", False)):
        cmd.insert(5, "DEBUG=1")
    run(cmd, env=env, dry_run=ctx.args.dry_run)

    flash = _pack_flash(ctx, bl1_bin(ctx), fip_bin(ctx))
    write_text(_tfa_build_stamp(ctx), tfa_build_key, ctx.args.dry_run)
    _write_qemu_run_script(ctx, flash)
    return flash
