# unified-workload

`unified-workload` 用来把 workload、rootfs/initramfs、Linux kernel、设备树和平台固件的制作流程统一到一个入口中，最终生成可以直接加载的镜像。

当前已经支持的默认目标是：

- 架构：`riscv`
- 平台：`xiangshan`
- profile：`hello`
- 最终产物：OpenSBI payload `fw_payload.bin`

这个仓库不会把 Linux、OpenSBI 这类大源码树直接提交进来。它们通过 `arch/<arch>/resources.json` 声明，并统一放在 `external/<arch>/` 下；如果目标目录已经存在，下载步骤会自动跳过。

## 目录结构

```text
.
├── workload.py                 # 统一命令入口
├── apps/                       # workload/app 源码
│   └── hello/
├── arch/                       # 架构相关资源和流程
│   └── riscv/
│       ├── resources.json      # Linux/OpenSBI 等外部资源声明
│       └── firmware/opensbi.py # RISC-V OpenSBI payload 构建流程
├── plat/                       # 平台相关资源和流程
│   └── xiangshan/
│       ├── platform.json       # XiangShan 平台配置
│       ├── workflow.py         # XiangShan 构建流程
│       ├── dts/DTSGen.py       # XiangShan 设备树生成器
│       └── configs/linux_defconfig
├── lib/                        # 公共构建逻辑
├── build/                      # 编译产物，git 忽略
├── external/                   # 下载或软链接的外部源码，git 忽略
└── cache/                      # 下载缓存，git 忽略
```

## 环境要求

需要宿主机上有这些工具：

```sh
git make tar bash dtc python3
```

RISC-V 交叉工具链不从宿主环境自动探测，必须通过 `--cross-compile` 显式传入前缀。例如：

```sh
export RISCV_CROSS=/path/to/riscv64-buildroot-linux-gnu-
```

其中 `RISCV_CROSS` 是前缀，不包含 `gcc`。脚本会使用 `${RISCV_CROSS}gcc` 作为 C 编译器。

需要编译器的命令包括：

```text
doctor
build-workload
build-kernel
build-firmware
build-opensbi
all
```

这些命令都需要传入：

```sh
--cross-compile "$RISCV_CROSS"
```

注意：宿主机是 x86 时，不能把宿主机上的 x86 动态库直接拷到 RISC-V rootfs/initramfs 中。当前默认 app 使用静态链接，`apps/hello/Makefile` 里的 `LDFLAGS += -static` 会生成 RISC-V 静态 ELF。

## 快速开始

默认可以直接在线获取外部资源：

```sh
python3 workload.py fetch
```

`fetch` 会把资源放到：

```text
external/riscv/linux
external/riscv/opensbi
```

如果本机已经有可用源码，手动把对应路径做成软链接即可，`fetch` 和后续构建都会把它当成已存在资源并跳过下载。例如：

```sh
mkdir -p external/riscv
ln -s /path/to/linux-6.10.3 external/riscv/linux
ln -s /path/to/opensbi external/riscv/opensbi
```

检查环境和资源：

```sh
python3 workload.py doctor --cross-compile "$RISCV_CROSS"
```

查看本次构建计划和产物路径：

```sh
python3 workload.py print-plan
```

一键构建默认 XiangShan Linux 镜像：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS"
```

默认流程会依次执行：

```text
build-workload -> build-dtb -> build-kernel -> build-firmware
```

`build-opensbi` 是当前 RISC-V/XiangShan 平台上 `build-firmware` 的兼容别名。

## 分步构建

只编译 workload 并生成 initramfs 描述文件：

```sh
python3 workload.py build-workload --cross-compile "$RISCV_CROSS"
```

只生成 XiangShan DTB：

```sh
python3 workload.py build-dtb
```

只编译带 initramfs 的 Linux `Image`：

```sh
python3 workload.py build-kernel --cross-compile "$RISCV_CROSS"
```

只生成平台固件 payload：

```sh
python3 workload.py build-firmware --cross-compile "$RISCV_CROSS"
```

## 产物路径

所有编译产物统一放在：

```text
build/plat/<platform>/<profile>/
```

默认 `xiangshan/hello` 的关键产物如下：

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

模拟器最终加载的镜像通常是：

```text
build/plat/xiangshan/hello/opensbi/platform/generic/firmware/fw_payload.bin
```

## 添加 workload

新的 workload 放到 `apps/<name>/` 下。最简单的 C app 可以复用公共 Makefile：

```make
NAME = myapp
SRCS = main.c
LDFLAGS += -static

UNIFIED_WORKLOAD_HOME ?= ../..
include $(UNIFIED_WORKLOAD_HOME)/Makefile.compile
```

然后用 `--workload` 指定：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --workload myapp
```

如果 app 源码不在本仓库，也可以传入外部目录或单个 C 文件：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --workload myapp --workload-dir /path/to/myapp
python3 workload.py all --cross-compile "$RISCV_CROSS" --workload myapp --workload-dir /path/to/main.c
```

`build-workload` 会把 workload 编译到 `build/plat/<platform>/<profile>/workload/`，并生成一个最小 initramfs 列表，把 workload 安装为 guest Linux 的 `/init`。

通常应通过 `workload.py` 构建 app。若需要直接进入 `apps/<name>/` 调用 Makefile，也必须显式传入 `CROSS_COMPILE=<prefix>`，公共 Makefile 不提供默认交叉工具链。

## 平台和架构配置

架构相关内容放在 `arch/<arch>/` 下。例如 RISC-V 的 Linux/OpenSBI 外部资源声明在：

```text
arch/riscv/resources.json
```

平台相关内容放在 `plat/<platform>/` 下。例如 XiangShan 的平台配置在：

```text
plat/xiangshan/platform.json
```

其中：

- `arch` 表示平台所属架构。
- `firmware` 表示平台固件制作类型。当前 XiangShan 使用 `opensbi`。
- `linux_defconfig` 指向平台使用的 Linux defconfig。
- `dts_generator` 指向平台使用的 DTS 生成器。
- `profiles` 定义不同 workload profile。

后续如果支持 ARM 或其他架构，可以继续添加 `arch/<arch>/` 和 `plat/<platform>/`。平台固件不强行命名为 bootloader，RISC-V 当前实现是 OpenSBI，其他架构可以扩展为 TF-A、EDK2 或对应平台需要的固件流程。

## 常用参数

指定平台、架构和 profile：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --arch riscv --platform xiangshan --profile hello
```

指定 hart 数量：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --harts 4
```

覆盖 Linux bootargs：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --bootargs "console=hvc0 earlycon=sbi"
```

指定并行编译任务数：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --jobs 16
```

只看命令不真正执行：

```sh
python3 workload.py all --cross-compile "$RISCV_CROSS" --dry-run
```

## 清理

当前没有单独的 `clean` 子命令。要清理本仓库编译产物，可以删除：

```text
build/
```

如果 Linux 源码树之前做过 in-tree build，外部 `O=...` 构建可能会报源码树不干净。可以在 Linux 源码目录执行：

```sh
make ARCH=riscv CROSS_COMPILE=/path/to/riscv64-buildroot-linux-gnu- mrproper
```

注意 `mrproper` 会清理 Linux 源码树中的配置和中间文件，只应在确认源码树里没有需要保留的本地构建状态后执行。
