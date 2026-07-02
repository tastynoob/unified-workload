# XiangShan GCPT Platform

`xiangshan-gcpt` 平台用于生成 checkpoint/SimPoint 场景下的 XiangShan workload 镜像。

启动链：

```text
gcpt -> OpenSBI -> Linux kernel -> user workload
```

## 平台属性

- 架构：`riscv`
- Linux `ARCH`：`riscv`
- 固件流程：LibCheckpoint/gcpt + OpenSBI `fw_payload`
- 设备树：复用 `plat/xiangshan/dts/DTSGen.py`
- 默认 profile：`hello`
- 默认 workload：`apps/hello`

最终模拟器加载：

```text
build/plat/xiangshan-gcpt/hello/gcpt/gcpt.bin
```

## 地址布局

```text
0x80000000: gcpt.bin
0x80100000: OpenSBI fw_payload
0x80200000: Linux Image
```

该平台会把 `0x80000000..0x80100000` 写进 DTS 的 `reserved-memory`，并设置：

```text
OpenSBI FW_PAYLOAD_OFFSET = 0x100000
LibCheckpoint link address = 0x80000000
LibCheckpoint payload position = 0x80100000
```

因此 OpenSBI 被 gcpt 放到 `0x80100000`，Linux 仍保持在 `0x80200000`。

## 环境要求

公共工具：

```sh
git make tar bash python3
```

平台额外工具：

```sh
dtc
```

需要 RISC-V Linux 用户态交叉工具链：

```sh
export RISCV_CROSS=/path/to/riscv64-buildroot-linux-gnu-
```

`RISCV_CROSS` 是前缀，不包含 `gcc`。

## 外部资源

架构资源来自：

```text
arch/riscv/resources.json
```

平台额外资源来自：

```text
plat/xiangshan-gcpt/platform.json
```

下载资源：

```sh
python3 workload.py fetch \
  --arch riscv \
  --platform xiangshan-gcpt
```

资源默认放在：

```text
external/riscv/linux
external/riscv/opensbi
external/riscv/libcheckpoint
```

如果本机已有源码，可以手动软链接：

```sh
mkdir -p external/riscv
ln -s /path/to/linux-6.10.3 external/riscv/linux
ln -s /path/to/opensbi external/riscv/opensbi
ln -s /path/to/LibCheckpoint external/riscv/libcheckpoint
```

LibCheckpoint 需要初始化 submodule；使用 `fetch` 下载时会自动执行 submodule update。

## 构建流程

检查环境和资源：

```sh
python3 workload.py doctor \
  --arch riscv \
  --platform xiangshan-gcpt \
  --cross-compile "$RISCV_CROSS"
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --arch riscv \
  --platform xiangshan-gcpt \
  --cross-compile "$RISCV_CROSS"
```

一键构建：

```sh
python3 workload.py all \
  --arch riscv \
  --platform xiangshan-gcpt \
  --cross-compile "$RISCV_CROSS"
```

分步构建：

```sh
python3 workload.py build-workload --arch riscv --platform xiangshan-gcpt --cross-compile "$RISCV_CROSS"
python3 workload.py build-dtb      --arch riscv --platform xiangshan-gcpt
python3 workload.py build-kernel   --arch riscv --platform xiangshan-gcpt --cross-compile "$RISCV_CROSS"
python3 workload.py build-gcpt     --arch riscv --platform xiangshan-gcpt --cross-compile "$RISCV_CROSS"
```

`build-gcpt` 是 `build-firmware` 在该平台上的兼容别名，会先生成 OpenSBI `fw_payload.bin`，再把它嵌入 `gcpt.bin`。

## 关键产物

```text
build/plat/xiangshan-gcpt/hello/workload/hello
build/plat/xiangshan-gcpt/hello/initramfs.txt
build/plat/xiangshan-gcpt/hello/dtb/xiangshan-gcpt.dts
build/plat/xiangshan-gcpt/hello/dtb/xiangshan-gcpt.dtb
build/plat/xiangshan-gcpt/hello/linux/arch/riscv/boot/Image
build/plat/xiangshan-gcpt/hello/linux/.config
build/plat/xiangshan-gcpt/hello/opensbi/platform/generic/firmware/fw_payload.bin
build/plat/xiangshan-gcpt/hello/gcpt/gcpt.bin
```
