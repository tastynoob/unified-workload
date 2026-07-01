# XiangShan Platform

`xiangshan` 平台用于生成面向 XiangShan/RISC-V 的最小 Linux workload 镜像。

## 平台属性

- 架构：`riscv`
- Linux `ARCH`：`riscv`
- 固件流程：OpenSBI `fw_payload`
- 设备树：由 `plat/xiangshan/dts/DTSGen.py` 生成
- 默认 profile：`hello`
- 默认 workload：`apps/hello`

最终模拟器通常加载：

```text
build/plat/xiangshan/hello/opensbi/platform/generic/firmware/fw_payload.bin
```

## 环境要求

公共工具：

```sh
git make tar bash python3
```

平台额外工具：

```sh
dtc
```

需要 RISC-V Linux 用户态交叉工具链，并显式传入前缀：

```sh
export RISCV_CROSS=/path/to/riscv64-buildroot-linux-gnu-
```

`RISCV_CROSS` 是前缀，不包含 `gcc`。

## 外部资源

默认资源声明在：

```text
arch/riscv/resources.json
```

下载资源：

```sh
python3 workload.py fetch --arch riscv --platform xiangshan
```

资源默认放在：

```text
external/riscv/linux
external/riscv/opensbi
```

如果本机已有源码，可以手动软链接：

```sh
mkdir -p external/riscv
ln -s /path/to/linux-6.10.3 external/riscv/linux
ln -s /path/to/opensbi external/riscv/opensbi
```

## 构建流程

检查环境和资源：

```sh
python3 workload.py doctor \
  --arch riscv \
  --platform xiangshan \
  --cross-compile "$RISCV_CROSS"
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --arch riscv \
  --platform xiangshan \
  --cross-compile "$RISCV_CROSS"
```

一键构建：

```sh
python3 workload.py all \
  --arch riscv \
  --platform xiangshan \
  --cross-compile "$RISCV_CROSS"
```

分步构建：

```sh
python3 workload.py build-workload --arch riscv --platform xiangshan --cross-compile "$RISCV_CROSS"
python3 workload.py build-dtb      --arch riscv --platform xiangshan
python3 workload.py build-kernel   --arch riscv --platform xiangshan --cross-compile "$RISCV_CROSS"
python3 workload.py build-opensbi  --arch riscv --platform xiangshan --cross-compile "$RISCV_CROSS"
```

`build-opensbi` 是 `build-firmware` 在该平台上的兼容别名。

## 关键产物

```text
build/plat/xiangshan/hello/workload/hello
build/plat/xiangshan/hello/initramfs.txt
build/plat/xiangshan/hello/dtb/xiangshan.dts
build/plat/xiangshan/hello/dtb/xiangshan.dtb
build/plat/xiangshan/hello/linux/arch/riscv/boot/Image
build/plat/xiangshan/hello/linux/.config
build/plat/xiangshan/hello/opensbi/platform/generic/firmware/fw_payload.elf
build/plat/xiangshan/hello/opensbi/platform/generic/firmware/fw_payload.bin
```

## 平台参数

常用覆盖参数：

```sh
--harts 4
--bootargs "console=hvc0 earlycon=sbi"
--memory-base 0x80000000
--memory-size 0x200000000
--serial-addr 0x40600000
--sd-addr 0x40002000
--timebase-frequency 10000000
--mmu-type riscv,sv48
--rva-profile rva23s64
```

默认值见：

```text
plat/xiangshan/platform.json
```

## 注意事项

workload 会被放进 initramfs 并作为 `/init` 执行。宿主机是 x86 时，不能把宿主机 x86 动态库拷进 RISC-V initramfs；默认 hello 使用静态链接。

如果 Linux 源码树之前做过 in-tree build，可以在 Linux 源码目录清理：

```sh
make ARCH=riscv CROSS_COMPILE="$RISCV_CROSS" mrproper
```
