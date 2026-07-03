# QEMU Mini-Virt AArch64 Platform

`qemu-minivirt-aarch64` 平台用于在自定义 `mini-virt` AArch64 QEMU
机器上验证 Linux workload 镜像。

## 平台属性

- 架构：`aarch64`
- Linux `ARCH`：`arm64`
- 固件流程：self-contained payload -> Linux
- 设备树：构建时生成静态 DTB，并嵌入 payload
- 默认 QEMU：`/home/lurker/workspace/arm64-simpoint/arm-qemu/build/qemu-system-aarch64`
- 默认 machine：`mini-virt`
- 默认 profile：`hello`
- 默认 workload：`apps/hello`

该平台生成一个一体化 AArch64 payload：boot stub、Linux `Image` 和静态
DTB 放在同一份二进制里。Linux `Image` 内嵌 initramfs，workload 安装为
guest Linux 的 `/init`。

最终入口：

```text
build/plat/qemu-minivirt-aarch64/hello/payload/aarch64-payload.bin
```

构建后还会生成可直接运行的 QEMU 脚本：

```text
build/plat/qemu-minivirt-aarch64/hello/run-qemu.sh
```

## Mini-Virt 设备布局

当前静态 DTB 描述的硬件布局与 `hw/arm/mini-virt.c` 对齐：

```text
RAM                 0x40000000
PL011 UART          0x09000000
GICv3 distributor   0x08000000
GICv3 redistributor 0x080a0000
```

PL011 使用 GIC SPI 1：

```text
PL011 UART interrupt SPI 1
```

ARM generic timer 使用 GIC PPI：

```text
secure physical     PPI 13
non-secure physical PPI 14
virtual             PPI 11
hypervisor          PPI 10
```

如果 `hw/arm/mini-virt.c` 退回 `pl011_create(..., NULL, ...)`，Linux 会显示
`ttyAMA0 ... irq = 0`。这种情况下内核 printk 可以输出，但用户态经
`/dev/console` 打印不一定能正常推进。

## 环境要求

公共工具：

```sh
git make tar bash python3 dtc
```

需要 AArch64 Linux 用户态交叉工具链，并显式传入前缀：

```sh
export AARCH64_CROSS=/home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-
```

`AARCH64_CROSS` 是前缀，不包含 `gcc`。

## 外部资源

该平台只需要 Linux 源码。若只下载必需资源：

```sh
python3 workload.py fetch linux \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64
```

如果本机已有 Linux 源码，可以手动软链接：

```sh
mkdir -p external/aarch64
ln -s /path/to/linux-6.10.3 external/aarch64/linux
```

## 构建流程

检查环境和资源：

```sh
python3 workload.py doctor \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

一键构建：

```sh
python3 workload.py all \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

分步构建：

```sh
python3 workload.py build-workload --arch aarch64 --platform qemu-minivirt-aarch64 --cross-compile "$AARCH64_CROSS"
python3 workload.py build-dtb      --arch aarch64 --platform qemu-minivirt-aarch64
python3 workload.py build-kernel   --arch aarch64 --platform qemu-minivirt-aarch64 --cross-compile "$AARCH64_CROSS"
python3 workload.py build-firmware --arch aarch64 --platform qemu-minivirt-aarch64 --cross-compile "$AARCH64_CROSS"
```

## 运行

构建完成后运行：

```sh
build/plat/qemu-minivirt-aarch64/hello/run-qemu.sh
```

如需临时覆盖 QEMU 路径：

```sh
QEMU_SYSTEM_AARCH64=/home/lurker/workspace/arm64-simpoint/arm-qemu/build/qemu-system-aarch64 \
  build/plat/qemu-minivirt-aarch64/hello/run-qemu.sh
```

默认 hello 进入 `/init` 后会打印：

```text
hello
hanging
```

若只验证内核启动和 timer/GIC 初始化，可以用 `timeout` 退出：

```sh
timeout 45s build/plat/qemu-minivirt-aarch64/hello/run-qemu.sh
```

## 关键产物

```text
build/plat/qemu-minivirt-aarch64/hello/workload/hello
build/plat/qemu-minivirt-aarch64/hello/initramfs.txt
build/plat/qemu-minivirt-aarch64/hello/initramfs.cpio
build/plat/qemu-minivirt-aarch64/hello/dtb/qemu-minivirt-aarch64.dts
build/plat/qemu-minivirt-aarch64/hello/dtb/qemu-minivirt-aarch64.dtb
build/plat/qemu-minivirt-aarch64/hello/linux/arch/arm64/boot/Image
build/plat/qemu-minivirt-aarch64/hello/linux/.config
build/plat/qemu-minivirt-aarch64/hello/payload/aarch64-payload.bin
build/plat/qemu-minivirt-aarch64/hello/payload/layout.txt
build/plat/qemu-minivirt-aarch64/hello/run-qemu.sh
```

`run-qemu.sh` 使用的主要参数：

```text
-machine mini-virt
-cpu cortex-a57
-kernel build/plat/qemu-minivirt-aarch64/hello/payload/aarch64-payload.bin
```

payload 里的 boot stub 会设置 `x0=<embedded dtb>`、`x1-x3=0` 后跳转到
Linux，因此 Linux 不依赖 QEMU 运行时传入 FDT。bootargs 会固化到 Linux
`CONFIG_CMDLINE`，保证 payload 不依赖 QEMU `-append`。
