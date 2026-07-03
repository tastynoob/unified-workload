from __future__ import annotations

from pathlib import Path

from arch.aarch64.firmware import payload as aarch64_payload
from lib.common import BuildError, run, write_text
from lib.context import BuildContext
from lib.linux import build_kernel as build_linux_kernel


def _to_int(value: str | int | None, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, int):
        return value
    return int(value, 0)


def doctor(ctx: BuildContext) -> list[Path]:
    required = [ctx.linux_defconfig()]
    return [path for path in required if not path.exists()]


def doctor_tools(ctx: BuildContext) -> list[str]:
    return ["dtc", str(ctx.default("qemu_binary", "qemu-system-aarch64"))]


def generate_dts(ctx: BuildContext) -> str:
    harts = ctx.harts()
    if harts != 1:
        raise BuildError("mini-virt supports exactly one CPU")

    memory_base = _to_int(ctx.memory_base(), 0x40000000)
    memory_size = _to_int(ctx.memory_size(), 0x40000000)

    return f"""\
/dts-v1/;

/ {{
    compatible = "unified-workload,qemu-minivirt-aarch64", "unified-workload,qemu-mini-virt";
    model = "unified-workload qemu-minivirt-aarch64";
    #address-cells = <2>;
    #size-cells = <2>;
    interrupt-parent = <&gic>;

    chosen {{
        stdout-path = "/pl011@9000000";
        bootargs = "{ctx.bootargs()}";
    }};

    memory@{memory_base:x} {{
        device_type = "memory";
        reg = <0x{memory_base >> 32:x} 0x{memory_base & 0xffffffff:x}
               0x{memory_size >> 32:x} 0x{memory_size & 0xffffffff:x}>;
    }};

    cpus {{
        #address-cells = <1>;
        #size-cells = <0>;

        cpu@0 {{
            device_type = "cpu";
            compatible = "arm,cortex-a57";
            reg = <0x0>;
        }};
    }};

    timer {{
        compatible = "arm,armv8-timer", "arm,armv7-timer";
        interrupts = <0x1 0xd 0x4>, <0x1 0xe 0x4>,
                     <0x1 0xb 0x4>, <0x1 0xa 0x4>;
        always-on;
    }};

    gic: interrupt-controller@8000000 {{
        compatible = "arm,gic-v3";
        #interrupt-cells = <3>;
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;
        interrupt-controller;
        #redistributor-regions = <1>;
        reg = <0x0 0x08000000 0x0 0x10000>,
              <0x0 0x080a0000 0x0 0xf60000>;
    }};

    apb_pclk: apb-pclk {{
        compatible = "fixed-clock";
        #clock-cells = <0>;
        clock-frequency = <24000000>;
        clock-output-names = "clk24mhz";
    }};

    pl011@9000000 {{
        compatible = "arm,pl011", "arm,primecell";
        reg = <0x00 0x09000000 0x00 0x1000>;
        interrupts = <0x0 0x1 0x4>;
        clocks = <&apb_pclk>, <&apb_pclk>;
        clock-names = "uartclk", "apb_pclk";
    }};
}};
"""


def build_dtb(ctx: BuildContext) -> Path:
    dts = ctx.dts_path()
    dtb = ctx.dtb_path()
    write_text(dts, generate_dts(ctx), ctx.args.dry_run)
    run(["dtc", "-I", "dts", "-O", "dtb", "-o", str(dtb), str(dts)], dry_run=ctx.args.dry_run)
    return dtb


def build_kernel(ctx: BuildContext) -> Path:
    return build_linux_kernel(ctx, ctx.linux_defconfig())


def _qemu_run_script(ctx: BuildContext) -> Path:
    return ctx.profile_build_dir() / "run-qemu.sh"


def _write_qemu_run_script(ctx: BuildContext, payload: Path) -> Path:
    script = _qemu_run_script(ctx)
    qemu = str(ctx.default("qemu_binary", "qemu-system-aarch64"))
    machine = str(ctx.default("qemu_machine", "mini-virt"))
    cpu = str(ctx.default("qemu_cpu", "cortex-a57"))
    memory = str(ctx.default("qemu_memory", "1024M"))
    content = f"""#!/usr/bin/env bash
set -euo pipefail

QEMU_SYSTEM_AARCH64="${{QEMU_SYSTEM_AARCH64:-{qemu}}}"

"$QEMU_SYSTEM_AARCH64" \\
  -machine {machine} \\
  -cpu {cpu} \\
  -smp {ctx.harts()} \\
  -m {memory} \\
  -nographic \\
  -kernel "{payload}"
"""
    write_text(script, content, ctx.args.dry_run)
    if not ctx.args.dry_run:
        script.chmod(0o755)
    return script


def build_firmware(ctx: BuildContext) -> Path:
    if ctx.firmware == "payload":
        payload = aarch64_payload.build(ctx)
        _write_qemu_run_script(ctx, payload)
        return payload
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")


def final_payload(ctx: BuildContext) -> Path:
    if ctx.firmware == "payload":
        return aarch64_payload.payload_bin(ctx)
    raise BuildError(f"Unsupported firmware for platform {ctx.platform}: {ctx.firmware}")
