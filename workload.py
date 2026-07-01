#!/usr/bin/env python3
"""CLI entry for unified workload image generation."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

from lib.apps import build_workload
from lib.common import BuildError, load_json, load_symbol, log
from lib.context import (
    DEFAULT_ARCH,
    DEFAULT_PLATFORM,
    DEFAULT_PROFILE,
    BuildContext,
    SCRIPT_DIR,
)
from lib.resources import (
    fetch_resource,
    resource_path,
)
from lib.toolchain import cross_gcc


CROSS_COMPILE_REQUIRED_COMMANDS = {
    "doctor",
    "build-workload",
    "build-kernel",
    "build-firmware",
    "build-opensbi",
    "build-tfa",
    "all",
}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build unified workload images")
    parser.add_argument(
        "command",
        choices=[
            "doctor",
            "fetch",
            "print-plan",
            "build-workload",
            "build-dtb",
            "build-kernel",
            "build-firmware",
            "build-opensbi",
            "build-tfa",
            "all",
        ],
    )
    parser.add_argument("resources", nargs="*", help="resource names for fetch")
    parser.add_argument("--config", type=Path, help="override arch resource config")
    parser.add_argument("--arch", default=DEFAULT_ARCH, help="architecture profile under unified-workload/arch")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="platform profile under unified-workload/plat")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--external-dir", type=Path, default=SCRIPT_DIR / "external")
    parser.add_argument("--cache-dir", type=Path, default=SCRIPT_DIR / "cache")
    parser.add_argument("--build-dir", type=Path, default=SCRIPT_DIR / "build")
    parser.add_argument(
        "--cross-compile",
        help="cross compiler prefix, for example /path/to/<target-triplet>-",
    )
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--workload", help="workload name under unified-workload/apps")
    parser.add_argument("--workload-dir", type=Path, help="external app source directory or C file")
    parser.add_argument("--cflags", action="append", default=[], help="extra workload CFLAGS")
    parser.add_argument("--ldflags", action="append", default=[], help="extra workload LDFLAGS")
    parser.add_argument("--device", dest="platform", help=argparse.SUPPRESS)
    parser.add_argument("--dts-generator", type=Path, help="override platform DTSGen.py path")
    parser.add_argument("--harts", type=int)
    parser.add_argument("--linux-defconfig", type=Path)
    parser.add_argument("--opensbi-platform")
    parser.add_argument("--bootargs")
    parser.add_argument("--memory-base")
    parser.add_argument("--memory-size")
    parser.add_argument("--serial-addr")
    parser.add_argument("--sd-addr")
    parser.add_argument("--timebase-frequency", type=int)
    parser.add_argument("--mmu-type")
    parser.add_argument("--rva-profile")
    parser.add_argument("--isa-extension", action="append", default=[], help="extra ISA extension for DTS")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def default_arch_config_path(args: argparse.Namespace) -> Path:
    return SCRIPT_DIR / "arch" / args.arch / "resources.json"


def platform_config_path(args: argparse.Namespace) -> Path:
    return SCRIPT_DIR / "plat" / args.platform / "platform.json"


def platform_workflow_path(args: argparse.Namespace) -> Path:
    return SCRIPT_DIR / "plat" / args.platform / "workflow.py"


def normalize_args(args: argparse.Namespace) -> None:
    args.config = (args.config or default_arch_config_path(args)).resolve()
    args.external_dir = args.external_dir.resolve()
    args.cache_dir = args.cache_dir.resolve()
    args.build_dir = args.build_dir.resolve()
    if args.command in CROSS_COMPILE_REQUIRED_COMMANDS and not args.cross_compile:
        raise BuildError(f"{args.command} requires --cross-compile")
    args.jobs = args.jobs if args.jobs is not None else (os_cpu_count())


def os_cpu_count() -> int:
    import os

    return os.cpu_count() or 1


def make_context(args: argparse.Namespace) -> BuildContext:
    platform_cfg_path = platform_config_path(args)
    if not platform_cfg_path.exists():
        raise BuildError(f"Platform config does not exist: {platform_cfg_path}")

    resource_config = load_json(args.config)
    if "resources" not in resource_config or not isinstance(resource_config["resources"], dict):
        raise BuildError(f"Invalid resource config: {args.config}")

    platform_config = load_json(platform_cfg_path)
    platform_arch = platform_config.get("arch")
    if platform_arch and platform_arch != args.arch:
        raise BuildError(f"Platform {args.platform} requires arch '{platform_arch}', got '{args.arch}'")

    workflow = load_symbol(platform_workflow_path(args), "build_firmware")
    workflow_module = sys.modules.get(workflow.__module__)
    if workflow_module is None:
        raise BuildError(f"Cannot load platform workflow: {platform_workflow_path(args)}")

    return BuildContext(args, resource_config, platform_config, workflow_module)


def command_doctor(ctx: BuildContext) -> None:
    tools = ["git", "make", "tar", "bash", cross_gcc(ctx.args.cross_compile)]
    doctor_tools = getattr(ctx.platform_workflow, "doctor_tools", None)
    if doctor_tools is not None:
        tools.extend(doctor_tools(ctx))

    missing: list[str] = []
    for tool in tools:
        found = shutil.which(tool)
        status = found if found else "missing"
        log(f"tool {tool}: {status}")
        if not found:
            missing.append(tool)

    for name in sorted(ctx.resource_config["resources"]):
        path = resource_path(ctx, name)
        resource_status = str(path) if path.exists() else "missing"
        log(f"resource {name}: {resource_status}")

    log(f"arch {ctx.arch}: resources={ctx.args.config}")
    log(f"platform {ctx.platform}: config={ctx.platform_config_path()}")
    log(f"platform {ctx.platform}: workflow={platform_workflow_path(ctx.args)}")
    log(f"platform {ctx.platform}: firmware={ctx.firmware}")
    log(f"profile {ctx.profile_name}: workload={ctx.selected_workload()}, app_dir={ctx.app_dir()}")

    if not ctx.app_dir().exists():
        missing.append(str(ctx.app_dir()))
    for path in ctx.platform_workflow.doctor(ctx):
        missing.append(str(path))

    if missing:
        raise BuildError("Missing required tools or paths: " + ", ".join(missing))


def command_fetch(ctx: BuildContext) -> None:
    names = ctx.args.resources or sorted(ctx.resource_config["resources"])
    for name in names:
        fetch_resource(ctx, name)


def command_print_plan(ctx: BuildContext) -> None:
    log(f"arch: {ctx.arch}")
    log(f"linux arch: {ctx.linux_arch}")
    log(f"platform: {ctx.platform}")
    log(f"resource config: {ctx.args.config}")
    log(f"platform config: {ctx.platform_config_path()}")
    log(f"platform workflow: {platform_workflow_path(ctx.args)}")
    log(f"firmware: {ctx.firmware}")
    log(f"profile: {ctx.profile_name}")
    log(f"workload: {ctx.selected_workload()}")
    log(f"app source: {ctx.app_dir()}")
    log(f"workload binary: {ctx.workload_binary()}")
    log(f"initramfs list: {ctx.initramfs_list()}")
    if ctx.args.dts_generator or ctx.platform_config.get("dts_generator"):
        log(f"dts generator: {ctx.dts_generator_path()}")
        log(f"dtb: {ctx.dtb_path()}")
    else:
        log("dtb: platform workflow does not use a static DTB")
    log(f"harts: {ctx.harts()}")
    for name in sorted(ctx.resource_config["resources"]):
        log(f"resource {name}: {resource_path(ctx, name)}")
    log(f"linux defconfig: {ctx.linux_defconfig()}")
    if "opensbi" in ctx.resource_config["resources"]:
        log(f"opensbi platform: {ctx.opensbi_platform}")
    log(f"build dir: {ctx.profile_build_dir()}")
    log(f"final payload: {ctx.platform_workflow.final_payload(ctx)}")


def command_all(ctx: BuildContext) -> None:
    build_workload(ctx)
    ctx.platform_workflow.build_dtb(ctx)
    ctx.platform_workflow.build_kernel(ctx)
    ctx.platform_workflow.build_firmware(ctx)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)

    try:
        normalize_args(args)
        ctx = make_context(args)
        if args.command == "doctor":
            command_doctor(ctx)
        elif args.command == "fetch":
            command_fetch(ctx)
        elif args.command == "print-plan":
            command_print_plan(ctx)
        elif args.command == "build-workload":
            build_workload(ctx)
        elif args.command == "build-dtb":
            ctx.platform_workflow.build_dtb(ctx)
        elif args.command == "build-kernel":
            ctx.platform_workflow.build_kernel(ctx)
        elif args.command in ("build-firmware", "build-opensbi", "build-tfa"):
            ctx.platform_workflow.build_firmware(ctx)
        elif args.command == "all":
            command_all(ctx)
        else:
            parser.error(f"unknown command: {args.command}")
    except (BuildError, subprocess.CalledProcessError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
