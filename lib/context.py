from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from lib.common import BuildError


SCRIPT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ARCH = "riscv"
DEFAULT_PLATFORM = "xiangshan"
DEFAULT_PROFILE = "hello"


@dataclass
class BuildContext:
    args: Any
    resource_config: Mapping[str, Any]
    platform_config: Mapping[str, Any]
    platform_workflow: Any

    @property
    def root_dir(self) -> Path:
        return SCRIPT_DIR

    @property
    def arch(self) -> str:
        return self.args.arch

    @property
    def platform(self) -> str:
        return self.args.platform

    @property
    def profile_name(self) -> str:
        return self.args.profile

    @property
    def profile(self) -> Mapping[str, Any]:
        profiles = self.platform_config.get("profiles", {})
        if self.profile_name not in profiles:
            names = ", ".join(sorted(profiles))
            raise BuildError(f"Unknown profile '{self.profile_name}'. Available profiles: {names}")
        return profiles[self.profile_name]

    @property
    def firmware(self) -> str:
        return str(self.platform_config.get("firmware", ""))

    @property
    def linux_arch(self) -> str:
        return str(self.platform_config.get("linux_arch", self.arch))

    @property
    def opensbi_platform(self) -> str:
        if self.args.opensbi_platform:
            return self.args.opensbi_platform
        opensbi = self.platform_config.get("opensbi", {})
        return str(opensbi.get("platform", "generic"))

    def default(self, name: str, fallback: Any = None) -> Any:
        return self.platform_config.get("defaults", {}).get(name, fallback)

    def profile_value(self, name: str, fallback: Any = None) -> Any:
        return self.profile.get(name, fallback)

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
        return self.args.workload or str(self.profile_value("workload"))

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
        if self.args.linux_defconfig is not None:
            return self.args.linux_defconfig.resolve()
        value = self.platform_config.get("linux_defconfig", "configs/linux_defconfig")
        return (self.platform_dir() / value).resolve()

    def dts_generator_path(self) -> Path:
        if self.args.dts_generator is not None:
            return self.args.dts_generator.resolve()
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
        value = self.args.harts
        if value is None:
            value = self.profile_value("harts", self.default("harts", 1))
        value = int(value)
        if value < 1:
            raise BuildError("--harts must be >= 1")
        return value

    def bootargs(self) -> str:
        return self.args.bootargs or str(self.default("bootargs", "console=hvc0 earlycon=sbi"))

    def memory_base(self) -> str:
        return self.args.memory_base or str(self.default("memory_base", "0x80000000"))

    def memory_size(self) -> str:
        return self.args.memory_size or str(self.default("memory_size", "0x200000000"))

    def serial_addr(self) -> Optional[str]:
        return self.args.serial_addr if self.args.serial_addr is not None else self.default("serial_addr", "0x40600000")

    def sd_addr(self) -> Optional[str]:
        return self.args.sd_addr if self.args.sd_addr is not None else self.default("sd_addr", "0x40002000")

    def timebase_frequency(self) -> int:
        return int(self.args.timebase_frequency or self.default("timebase_frequency", 10000000))

    def mmu_type(self) -> str:
        return self.args.mmu_type or str(self.default("mmu_type", "riscv,sv48"))

    def rva_profile(self) -> Optional[str]:
        return self.args.rva_profile if self.args.rva_profile is not None else self.default("rva_profile", "rva23s64")
