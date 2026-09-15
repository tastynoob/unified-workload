from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from lib.common import BuildError


SCRIPT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM = "xiangshan"
DEFAULT_PROFILE = "hello"


@dataclass
class BuildContext:
    args: Any
    resource_config: Mapping[str, Any]
    platform_config: Mapping[str, Any]
    platform_workflow: Any
    platform_options: Mapping[str, list[str]]
    workload_options: Mapping[str, list[str]]

    @property
    def root_dir(self) -> Path:
        return SCRIPT_DIR

    @property
    def arch(self) -> str:
        return str(self.platform_config["arch"])

    @property
    def platform(self) -> str:
        return self.args.platform

    @property
    def profile_name(self) -> str:
        return self.args.profile

    @property
    def firmware(self) -> str:
        return str(self.platform_config.get("firmware", ""))

    @property
    def linux_arch(self) -> str:
        return str(self.platform_config.get("linux_arch", self.arch))

    @property
    def opensbi_platform(self) -> str:
        value = self.platform_option("opensbi_platform")
        if value is not None:
            return value
        opensbi = self.platform_config.get("opensbi", {})
        return str(opensbi.get("platform", "generic"))

    def default(self, name: str, fallback: Any = None) -> Any:
        return self.platform_config.get("defaults", {}).get(name, fallback)

    def platform_option(self, name: str, fallback: Any = None) -> Any:
        values = self.platform_options.get(name)
        return values[-1] if values else fallback

    def platform_option_values(self, name: str) -> list[str]:
        return list(self.platform_options.get(name, []))

    def workload_option(self, name: str, fallback: Any = None) -> Any:
        values = self.workload_options.get(name)
        return values[-1] if values else fallback

    def workload_option_values(self, name: str) -> list[str]:
        return list(self.workload_options.get(name, []))

    def build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["ARCH"] = self.linux_arch
        if self.args.cross_compile:
            env["CROSS_COMPILE"] = self.args.cross_compile
        else:
            env.pop("CROSS_COMPILE", None)
        return env

    def arch_dir(self) -> Path:
        return self.root_dir / "arch" / self.arch

    def arch_resource_config_path(self) -> Path:
        return self.arch_dir() / "resources.json"

    def platform_dir(self) -> Path:
        return self.root_dir / "plat" / self.platform

    def platform_config_path(self) -> Path:
        return self.platform_dir() / "platform.json"

    def profile_build_dir(self) -> Path:
        return self.args.build_dir / "plat" / self.platform / self.profile_name

    def selected_workload(self) -> str:
        return self.args.workload or self.profile_name

    def app_dir(self) -> Path:
        if self.args.workload_dir is not None:
            return self.args.workload_dir.resolve()
        return self.root_dir / "apps" / self.selected_workload()

    def workload_binary(self) -> Path:
        return self.profile_build_dir() / "workload" / self.selected_workload()

    def initramfs_list(self) -> Path:
        return self.profile_build_dir() / "initramfs.txt"

    def initramfs_cpio(self) -> Path:
        return self.profile_build_dir() / "initramfs.cpio"

    def linux_image(self) -> Path:
        return self.profile_build_dir() / "linux" / "arch" / self.linux_arch / "boot" / "Image"

    def dtb_path(self) -> Path:
        return self.profile_build_dir() / "dtb" / f"{self.platform}.dtb"

    def dts_path(self) -> Path:
        return self.profile_build_dir() / "dtb" / f"{self.platform}.dts"

    def linux_defconfig(self) -> Path:
        value = self.platform_option("linux_defconfig")
        if value is not None:
            return Path(value).expanduser().resolve()
        value = self.platform_config.get("linux_defconfig", "configs/linux_defconfig")
        return (self.platform_dir() / value).resolve()

    def dts_generator_path(self) -> Path:
        value = self.platform_option("dts_generator")
        if value is not None:
            return Path(value).expanduser().resolve()
        value = self.platform_config.get("dts_generator", "dts/DTSGen.py")
        return (self.platform_dir() / value).resolve()

    def fw_payload_bin(self) -> Path:
        return (
            self.profile_build_dir()
            / "opensbi"
            / "platform"
            / self.opensbi_platform
            / "firmware"
            / "fw_payload.bin"
        )

    def harts(self) -> int:
        value = self.platform_option("harts", self.default("harts", 1))
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise BuildError("platform option harts must be an integer") from exc
        if value < 1:
            raise BuildError("platform option harts must be >= 1")
        return value

    def bootargs(self) -> str:
        return self.platform_option(
            "bootargs", str(self.default("bootargs", "console=hvc0 earlycon=sbi"))
        )

    def memory_base(self) -> str:
        return self.platform_option(
            "memory_base", str(self.default("memory_base", "0x80000000"))
        )

    def memory_size(self) -> str:
        return self.platform_option(
            "memory_size", str(self.default("memory_size", "0x200000000"))
        )

    def serial_addr(self) -> Optional[str]:
        return self.platform_option(
            "serial_addr", self.default("serial_addr", "0x40600000")
        )

    def sd_addr(self) -> Optional[str]:
        return self.platform_option(
            "sd_addr", self.default("sd_addr", "0x40002000")
        )

    def timebase_frequency(self) -> int:
        value = self.platform_option(
            "timebase_frequency", self.default("timebase_frequency", 10000000)
        )
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise BuildError(
                "platform option timebase_frequency must be an integer"
            ) from exc

    def mmu_type(self) -> str:
        return self.platform_option(
            "mmu_type", str(self.default("mmu_type", "riscv,sv48"))
        )

    def rva_profile(self) -> Optional[str]:
        return self.platform_option("rva_profile", self.default("rva_profile", "rva23s64"))
