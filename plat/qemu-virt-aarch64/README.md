# QEMU Virt AArch64 Platform

`qemu-virt-aarch64` 平台用于在 `qemu-system-aarch64` 上验证 AArch64 Linux workload 镜像。

## 平台属性

- 架构：`aarch64`
- Linux `ARCH`：`arm64`
- 固件流程：TF-A -> U-Boot -> Linux
- 设备树：QEMU virt 运行时生成并传递
- 默认 profile：`hello`
- 默认 workload：`apps/hello`

最终固件入口：

```text
build/plat/qemu-virt-aarch64/hello/tfa/flash.bin
```

构建后还会生成可直接运行的 QEMU 脚本：

```text
build/plat/qemu-virt-aarch64/hello/run-qemu.sh
```

## 环境要求

公共工具：

```sh
git make tar bash python3
```

平台额外工具：

```sh
qemu-system-aarch64
```

需要 AArch64 Linux 用户态交叉工具链，并显式传入前缀：

```sh
export AARCH64_CROSS=/path/to/aarch64-none-linux-gnu-
```

`AARCH64_CROSS` 是前缀，不包含 `gcc`。注意不要使用只能编 bare-metal 程序的工具链，workload 需要能生成 Linux 用户态 ELF。

## 外部资源

资源声明在：

```text
arch/aarch64/resources.json
```

下载资源：

```sh
python3 workload.py fetch \
  --arch aarch64 \
  --platform qemu-virt-aarch64
```

资源默认放在：

```text
external/aarch64/linux
external/aarch64/trusted-firmware-a
external/aarch64/u-boot
```

如果本机已有源码，可以手动软链接：

```sh
mkdir -p external/aarch64
ln -s /path/to/linux-6.10.3 external/aarch64/linux
ln -s /path/to/trusted-firmware-a external/aarch64/trusted-firmware-a
ln -s /path/to/u-boot external/aarch64/u-boot
```

## 构建流程

检查环境和资源：

```sh
python3 workload.py doctor \
  --arch aarch64 \
  --platform qemu-virt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --arch aarch64 \
  --platform qemu-virt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

一键构建：

```sh
python3 workload.py all \
  --arch aarch64 \
  --platform qemu-virt-aarch64 \
  --cross-compile "$AARCH64_CROSS"
```

分步构建：

```sh
python3 workload.py build-workload --arch aarch64 --platform qemu-virt-aarch64 --cross-compile "$AARCH64_CROSS"
python3 workload.py build-dtb      --arch aarch64 --platform qemu-virt-aarch64
python3 workload.py build-kernel   --arch aarch64 --platform qemu-virt-aarch64 --cross-compile "$AARCH64_CROSS"
python3 workload.py build-tfa      --arch aarch64 --platform qemu-virt-aarch64 --cross-compile "$AARCH64_CROSS"
```

`build-tfa` 是 `build-firmware` 在该平台上的兼容别名。`build-dtb` 只生成 marker，真实 DTB 由 QEMU 运行时提供。

## 运行

构建完成后运行：

```sh
build/plat/qemu-virt-aarch64/hello/run-qemu.sh
```

默认 hello 会输出：

```text
hello
hanging
```

`hanging` 后 workload 会进入死循环，方便模拟器停在用户态。如果只是验证启动，可以用 `timeout` 退出：

```sh
timeout 45s build/plat/qemu-virt-aarch64/hello/run-qemu.sh
```

## 关键产物

```text
build/plat/qemu-virt-aarch64/hello/workload/hello
build/plat/qemu-virt-aarch64/hello/initramfs.txt
build/plat/qemu-virt-aarch64/hello/initramfs.cpio
build/plat/qemu-virt-aarch64/hello/linux/arch/arm64/boot/Image
build/plat/qemu-virt-aarch64/hello/linux/.config
build/plat/qemu-virt-aarch64/hello/u-boot/u-boot.bin
build/plat/qemu-virt-aarch64/hello/tfa/qemu/release/bl1.bin
build/plat/qemu-virt-aarch64/hello/tfa/qemu/release/fip.bin
build/plat/qemu-virt-aarch64/hello/tfa/flash.bin
build/plat/qemu-virt-aarch64/hello/run-qemu.sh
```

`run-qemu.sh` 使用的主要参数：

```text
-machine virt,secure=on
-cpu cortex-a57
-bios build/plat/qemu-virt-aarch64/hello/tfa/flash.bin
-kernel build/plat/qemu-virt-aarch64/hello/linux/arch/arm64/boot/Image
-initrd build/plat/qemu-virt-aarch64/hello/initramfs.cpio
-append "console=ttyAMA0 earlycon"
```

## 注意事项

U-Boot 的 `TOOLS_MKEFICAPSULE` 在该平台默认关闭，避免构建 host-side EFI capsule 工具时额外依赖宿主机 `gnutls` 开发库。这个开关只影响 U-Boot host 工具，不影响当前 QEMU 启动链。

如果 Linux 源码树之前做过 in-tree build，可以在 Linux 源码目录清理：

```sh
make ARCH=arm64 CROSS_COMPILE="$AARCH64_CROSS" mrproper
```
