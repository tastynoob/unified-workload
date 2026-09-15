#!/usr/bin/env python3
"""CLI entry for unified workload image generation."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

from lib.apps import build_workload, validate_workload, workload_doctor
from lib.common import BuildError, load_json, log
from lib.context import (
    DEFAULT_PLATFORM,
    DEFAULT_PROFILE,
    BuildContext,
    SCRIPT_DIR,
)
from lib.platform import load_platform, parse_options
from lib.resources import (
    fetch_resource,
    resource_names,
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
    "build-gcpt",
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
            "build-gcpt",
            "all",
        ],
    )
    parser.add_argument("resources", nargs="*", help="resource names for fetch")
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
    parser.add_argument(
        "--platform-option", action="append", default=[], metavar="KEY=VALUE",
        help="platform-specific option; validated by the platform workflow",
    )
    parser.add_argument(
        "--workload-option", action="append", default=[], metavar="KEY=VALUE",
        help="workload-specific option; interpreted by the selected workload",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def platform_workflow_path(args: argparse.Namespace) -> Path:
    return SCRIPT_DIR / "plat" / args.platform / "workflow.py"


def normalize_args(args: argparse.Namespace) -> None:
    args.external_dir = args.external_dir.resolve()
    args.cache_dir = args.cache_dir.resolve()
    args.build_dir = args.build_dir.resolve()
    args.platform_options = parse_options(args.platform_option, "--platform-option")
    args.workload_options = parse_options(args.workload_option, "--workload-option")
    if args.command in CROSS_COMPILE_REQUIRED_COMMANDS and not args.cross_compile:
        raise BuildError(f"{args.command} requires --cross-compile")
    args.jobs = args.jobs if args.jobs is not None else (os_cpu_count())


def os_cpu_count() -> int:
    import os

    return os.cpu_count() or 1


def make_context(args: argparse.Namespace) -> BuildContext:
    platform_config, workflow_module, platform_cfg_path = load_platform(
        SCRIPT_DIR, args.platform
    )
    arch = str(platform_config.get("arch", ""))
    if not arch:
        raise BuildError(f"Platform config has no arch: {platform_cfg_path}")
    resource_config = load_json(SCRIPT_DIR / "arch" / arch / "resources.json")
    if "resources" not in resource_config or not isinstance(resource_config["resources"], dict):
        raise BuildError(f"Invalid resource config: {SCRIPT_DIR / 'arch' / arch / 'resources.json'}")

    platform_resources = platform_config.get("resources", {})
    if platform_resources and not isinstance(platform_resources, dict):
        raise BuildError(f"Invalid platform resources config: {platform_cfg_path}")
    ctx = BuildContext(
        args,
        resource_config,
        platform_config,
        workflow_module,
        args.platform_options,
        args.workload_options,
    )
    validate_options = getattr(workflow_module, "validate_options", None)
    if validate_options is not None:
        validate_options(ctx)
    validate_workload(ctx)
    return ctx


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

    for name in resource_names(ctx):
        path = resource_path(ctx, name)
        resource_status = str(path) if path.exists() else "missing"
        log(f"resource {name}: {resource_status}")

    log(f"arch {ctx.arch}: resources={ctx.arch_resource_config_path()}")
    log(f"platform {ctx.platform}: config={ctx.platform_config_path()}")
    log(f"platform {ctx.platform}: workflow={platform_workflow_path(ctx.args)}")
    log(f"platform {ctx.platform}: firmware={ctx.firmware}")
    log(f"profile {ctx.profile_name}: workload={ctx.selected_workload()}, app_dir={ctx.app_dir()}")

    if not ctx.app_dir().exists():
        missing.append(str(ctx.app_dir()))
    workload_doctor(ctx)
    for path in ctx.platform_workflow.doctor(ctx):
        missing.append(str(path))

    if missing:
        raise BuildError("Missing required tools or paths: " + ", ".join(missing))


def command_fetch(ctx: BuildContext) -> None:
    names = ctx.args.resources or resource_names(ctx)
    for name in names:
        fetch_resource(ctx, name)


def command_print_plan(ctx: BuildContext) -> None:
    log(f"arch: {ctx.arch}")
    log(f"linux arch: {ctx.linux_arch}")
    log(f"platform: {ctx.platform}")
    log(f"resource config: {ctx.arch_resource_config_path()}")
    log(f"platform config: {ctx.platform_config_path()}")
    log(f"platform workflow: {platform_workflow_path(ctx.args)}")
    log(f"firmware: {ctx.firmware}")
    log(f"profile: {ctx.profile_name}")
    log(f"workload: {ctx.selected_workload()}")
    log(f"app source: {ctx.app_dir()}")
    log(f"workload options: {ctx.workload_options}")
    log(f"workload binary: {ctx.workload_binary()}")
    log(f"initramfs list: {ctx.initramfs_list()}")
    dtb_mode = ctx.platform_config.get("dtb", {}).get("mode") if isinstance(ctx.platform_config.get("dtb"), dict) else None
    if "dts_generator" in ctx.platform_options or ctx.platform_config.get("dts_generator"):
        log(f"dts generator: {ctx.dts_generator_path()}")
        log(f"dts: {ctx.dts_path()}")
        log(f"dtb: {ctx.dtb_path()}")
    elif dtb_mode == "static":
        log(f"dts: {ctx.dts_path()}")
        log(f"dtb: {ctx.dtb_path()}")
    else:
        log("dtb: platform workflow does not use a static DTB")
    log(f"harts: {ctx.harts()}")
    for name in resource_names(ctx):
        log(f"resource {name}: {resource_path(ctx, name)}")
    log(f"linux defconfig: {ctx.linux_defconfig()}")
    if "opensbi" in resource_names(ctx):
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
        elif args.command in ("build-firmware", "build-opensbi", "build-tfa", "build-gcpt"):
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
