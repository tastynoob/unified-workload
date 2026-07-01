# unified-workload

`unified-workload` 是一个 workload-first 的镜像生成框架，用来把 workload、initramfs、Linux kernel、设备树和平台固件的制作流程统一到一个入口中。

它生成的是面向模拟器、验证环境或 bring-up 的最小可加载镜像，不是 Ubuntu、Buildroot 这类完整发行版 rootfs。

## 支持范围

| Platform | Arch | Firmware flow | Platform doc |
| --- | --- | --- | --- |
| `xiangshan` | `riscv` | OpenSBI payload | [`plat/xiangshan/README.md`](plat/xiangshan/README.md) |
| `qemu-virt-aarch64` | `aarch64` | TF-A -> U-Boot | [`plat/qemu-virt-aarch64/README.md`](plat/qemu-virt-aarch64/README.md) |

后续新增平台时，主 README 只记录公共约定；具体平台的资源、构建命令、产物路径和运行方式放在 `plat/<platform>/README.md`。

## 核心约定

- `apps/<name>/`：workload 源码。默认会把 workload 编译成 guest Linux 的 `/init`。
- `arch/<arch>/`：架构相关资源和固件流程，例如 Linux、OpenSBI、TF-A、U-Boot。
- `plat/<platform>/`：平台相关配置和流程，例如设备树、Linux defconfig、平台 README。
- `build/`：所有构建产物，git 忽略。
- `external/`：下载或软链接的外部源码树，git 忽略。
- `cache/`：下载缓存，git 忽略。

外部大源码树不会提交进仓库。资源通过 `arch/<arch>/resources.json` 声明，默认放在 `external/<arch>/` 下；如果目标目录已经存在，下载步骤会跳过。用户可以手动创建软链接来复用已有源码。

## 目录结构

```text
.
├── workload.py                 # 统一命令入口
├── apps/                       # workload/app 源码
├── arch/                       # 架构相关资源和固件流程
├── plat/                       # 平台相关配置、流程和文档
├── lib/                        # 公共构建逻辑
├── build/                      # 编译产物，git 忽略
├── external/                   # 外部源码树，git 忽略
└── cache/                      # 下载缓存，git 忽略
```

## 环境要求

公共依赖：

```sh
git make tar bash python3
```

交叉工具链不会从宿主环境自动探测，必须通过 `--cross-compile` 显式传入前缀：

```sh
python3 workload.py doctor \
  --arch <arch> \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

这里的 `--cross-compile` 是前缀，不包含 `gcc`。脚本会使用 `/path/to/<target-triplet>-gcc`。

宿主机是 x86 时，不能把宿主机上的 x86 动态库直接拷进目标 initramfs。默认 `apps/hello` 使用静态链接；真实 workload 也应该使用目标架构的 Linux 用户态工具链编译。

平台额外依赖见各平台 README。

## 通用命令

下载资源：

```sh
python3 workload.py fetch --arch <arch> --platform <platform>
```

如果本机已经有源码，直接软链接到对应 `external/<arch>/<dest>` 即可：

```sh
mkdir -p external/<arch>
ln -s /path/to/linux external/<arch>/linux
```

检查工具、资源和平台配置：

```sh
python3 workload.py doctor \
  --arch <arch> \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --arch <arch> \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

一键构建：

```sh
python3 workload.py all \
  --arch <arch> \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

默认流程：

```text
build-workload -> build-dtb -> build-kernel -> build-firmware
```

分步构建：

```sh
python3 workload.py build-workload --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>-
python3 workload.py build-dtb      --arch <arch> --platform <platform>
python3 workload.py build-kernel   --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>-
python3 workload.py build-firmware --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>-
```

平台可以提供兼容别名。例如 RISC-V/XiangShan 使用 `build-opensbi`，AArch64/QEMU virt 使用 `build-tfa`。

## 添加 Workload

新的 workload 放到 `apps/<name>/` 下。最简单的 C app 可以复用公共 Makefile：

```make
NAME = myapp
SRCS = main.c
LDFLAGS += -static

UNIFIED_WORKLOAD_HOME ?= ../..
include $(UNIFIED_WORKLOAD_HOME)/Makefile.compile
```

构建时通过 `--workload` 指定：

```sh
python3 workload.py all \
  --arch <arch> \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>- \
  --workload myapp
```

如果 app 源码不在本仓库，也可以传入外部目录或单个 C 文件：

```sh
python3 workload.py all --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>- --workload myapp --workload-dir /path/to/myapp
python3 workload.py all --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>- --workload myapp --workload-dir /path/to/main.c
```

`build-workload` 会把 workload 编译到：

```text
build/plat/<platform>/<profile>/workload/
```

并生成最小 initramfs 描述文件，把 workload 安装为 guest Linux 的 `/init`。

## 配置扩展

架构资源声明放在：

```text
arch/<arch>/resources.json
```

平台配置放在：

```text
plat/<platform>/platform.json
```

常用字段：

- `arch`：平台所属架构。
- `firmware`：平台固件制作类型，例如 `opensbi` 或 `tfa`。
- `linux_arch`：Linux Kbuild 使用的 `ARCH` 名称。未设置时默认等于 `arch`。
- `linux_defconfig`：平台使用的 Linux defconfig。
- `dts_generator`：平台使用的 DTS 生成器。
- `profiles`：不同 workload profile。

平台构建逻辑放在：

```text
plat/<platform>/workflow.py
```

架构固件流程可以放在：

```text
arch/<arch>/firmware/
```

## 常用参数

指定 profile：

```sh
python3 workload.py all --arch <arch> --platform <platform> --profile hello --cross-compile /path/to/<target-triplet>-
```

指定 hart/CPU 数量：

```sh
python3 workload.py all --arch <arch> --platform <platform> --harts 4 --cross-compile /path/to/<target-triplet>-
```

覆盖 Linux bootargs：

```sh
python3 workload.py all --arch <arch> --platform <platform> --bootargs "console=ttyAMA0 earlycon" --cross-compile /path/to/<target-triplet>-
```

指定并行编译任务数：

```sh
python3 workload.py all --arch <arch> --platform <platform> --jobs 16 --cross-compile /path/to/<target-triplet>-
```

只看命令不真正执行：

```sh
python3 workload.py all --arch <arch> --platform <platform> --cross-compile /path/to/<target-triplet>- --dry-run
```

## 清理

当前没有单独的 `clean` 子命令。要清理本仓库编译产物，可以删除：

```text
build/
```

如果 Linux 源码树之前做过 in-tree build，外部 `O=...` 构建可能会报源码树不干净。可以在 Linux 源码目录执行对应架构的 `mrproper`：

```sh
make ARCH=<linux-arch> CROSS_COMPILE=/path/to/<target-triplet>- mrproper
```
