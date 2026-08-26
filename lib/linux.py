from __future__ import annotations

import os
import shutil
from pathlib import Path

from lib.common import BuildError, log, run
from lib.context import BuildContext
from lib.resources import ensure_resource


def set_linux_config(config_path: Path, key: str, value: str) -> None:
    if not config_path.exists():
        raise BuildError(f"Linux config does not exist: {config_path}")

    new_line = f'{key}="{value}"\n'
    prefix = f"{key}="
    disabled = f"# {key} is not set"
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)

    replaced = False
    result = []
    for line in lines:
        if line.startswith(prefix) or line.startswith(disabled):
            result.append(new_line)
            replaced = True
        else:
            result.append(line)
    if not replaced:
        result.append(new_line)

    config_path.write_text("".join(result), encoding="utf-8")


def set_linux_config_bool(config_path: Path, key: str, enabled: bool) -> None:
    if not config_path.exists():
        raise BuildError(f"Linux config does not exist: {config_path}")

    new_line = f"{key}=y\n" if enabled else f"# {key} is not set\n"
    prefix = f"{key}="
    disabled = f"# {key} is not set"
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)

    replaced = False
    result = []
    for line in lines:
        if line.startswith(prefix) or line.startswith(disabled):
            result.append(new_line)
            replaced = True
        else:
            result.append(line)
    if not replaced:
        result.append(new_line)

    config_path.write_text("".join(result), encoding="utf-8")


def build_kernel(ctx: BuildContext, defconfig: Path) -> Path:
    linux = ensure_resource(ctx, "linux")
    initramfs = ctx.initramfs_list()
    if not initramfs.exists() and not ctx.args.dry_run:
        raise BuildError(f"initramfs list is missing: {initramfs}. Run build-workload first.")

    defconfig = defconfig.resolve()
    if not defconfig.exists():
        raise BuildError(f"Linux defconfig does not exist: {defconfig}")

    configured_build_dir = os.environ.get("LINUX_KBUILD_DIR")
    build_dir = (
        Path(configured_build_dir).expanduser().resolve()
        if configured_build_dir
        else ctx.profile_build_dir() / "linux"
    )
    linux_config = build_dir / ".config"
    log(f"install Linux config {defconfig} -> {linux_config}")
    if not ctx.args.dry_run:
        build_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(defconfig, linux_config)

    if ctx.args.dry_run:
        log(f"set CONFIG_INITRAMFS_SOURCE={initramfs}")
    else:
        set_linux_config(linux_config, "CONFIG_INITRAMFS_SOURCE", str(initramfs.resolve()))
        if bool(ctx.platform_config.get("linux_embed_bootargs", False)):
            set_linux_config(linux_config, "CONFIG_CMDLINE", ctx.bootargs())
            set_linux_config_bool(linux_config, "CONFIG_CMDLINE_FORCE", True)
            set_linux_config_bool(linux_config, "CONFIG_CMDLINE_FROM_BOOTLOADER", False)

    env = ctx.build_env()
    run(
        [
            "make",
            "-C",
            str(linux),
            f"O={build_dir}",
            f"ARCH={ctx.linux_arch}",
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
            str(linux),
            f"O={build_dir}",
            f"ARCH={ctx.linux_arch}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )

    image = build_dir / "arch" / ctx.linux_arch / "boot" / "Image"
    output_image = ctx.linux_image()
    if not ctx.args.dry_run and not image.exists():
        raise BuildError(f"Expected Linux Image does not exist: {image}")
    if not ctx.args.dry_run and image.resolve() != output_image.resolve():
        log(f"install Linux Image {image} -> {output_image}")
        output_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image, output_image)

    generated_initramfs = build_dir / "usr" / "initramfs_data.cpio"
    initramfs_cpio = ctx.initramfs_cpio()
    log(f"install initramfs cpio {generated_initramfs} -> {initramfs_cpio}")
    if not ctx.args.dry_run:
        if not generated_initramfs.exists():
            raise BuildError(f"Expected initramfs cpio does not exist: {generated_initramfs}")
        initramfs_cpio.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(generated_initramfs, initramfs_cpio)
    return output_image
