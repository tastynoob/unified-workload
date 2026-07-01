from __future__ import annotations

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


def build_kernel(ctx: BuildContext, defconfig: Path) -> Path:
    linux = ensure_resource(ctx, "linux")
    initramfs = ctx.initramfs_list()
    if not initramfs.exists():
        raise BuildError(f"initramfs list is missing: {initramfs}. Run build-workload first.")

    defconfig = defconfig.resolve()
    if not defconfig.exists():
        raise BuildError(f"Linux defconfig does not exist: {defconfig}")

    defconfig_name = f"unified_{ctx.platform}_defconfig"
    defconfig_dst = linux / "arch" / ctx.arch / "configs" / defconfig_name
    log(f"install Linux defconfig {defconfig} -> {defconfig_dst}")
    if not ctx.args.dry_run:
        defconfig_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(defconfig, defconfig_dst)

    build_dir = ctx.profile_build_dir() / "linux"
    env = ctx.build_env()
    run(
        [
            "make",
            "-C",
            str(linux),
            f"O={build_dir}",
            f"ARCH={ctx.arch}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            defconfig_name,
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )

    linux_config = build_dir / ".config"
    if ctx.args.dry_run:
        log(f"set CONFIG_INITRAMFS_SOURCE={initramfs}")
    else:
        set_linux_config(linux_config, "CONFIG_INITRAMFS_SOURCE", str(initramfs.resolve()))

    run(
        [
            "make",
            "-C",
            str(linux),
            f"O={build_dir}",
            f"ARCH={ctx.arch}",
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
            f"ARCH={ctx.arch}",
            f"CROSS_COMPILE={ctx.args.cross_compile}",
            "-j",
            str(ctx.args.jobs),
        ],
        env=env,
        dry_run=ctx.args.dry_run,
    )

    image = ctx.linux_image()
    if not ctx.args.dry_run and not image.exists():
        raise BuildError(f"Expected Linux Image does not exist: {image}")
    return image
