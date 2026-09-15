# unified-workload

`unified-workload` 是一个 workload-first 的镜像生成框架，用来把 workload、initramfs、Linux kernel、设备树和平台固件的制作流程统一到一个入口中。

它生成的是面向模拟器、验证环境或 bring-up 的最小可加载镜像，不是 Ubuntu、Buildroot 这类完整发行版 rootfs。

## 支持范围

| Platform | Arch | Firmware flow | Platform doc |
| --- | --- | --- | --- |
| `xiangshan` | `riscv` | OpenSBI payload | [`plat/xiangshan/README.md`](plat/xiangshan/README.md) |
| `xiangshan-gcpt` | `riscv` | gcpt -> OpenSBI payload | [`plat/xiangshan-gcpt/README.md`](plat/xiangshan-gcpt/README.md) |
| `qemu-minivirt-aarch64` | `aarch64` | self-contained payload | [`plat/qemu-minivirt-aarch64/README.md`](plat/qemu-minivirt-aarch64/README.md) |
| `qemu-minivirt-aarch64-gcpt` | `aarch64` | gcpt -> self-contained payload | [`plat/qemu-minivirt-aarch64-gcpt/README.md`](plat/qemu-minivirt-aarch64-gcpt/README.md) |

后续新增平台时，主 README 只记录公共约定；具体平台的资源、构建命令、产物路径和运行方式放在 `plat/<platform>/README.md`。

## 核心约定

- `apps/<name>/`：workload 源码。默认会把 workload 编译成 guest Linux 的 `/init`。
- `arch/<arch>/`：架构相关资源和固件流程，例如 Linux、OpenSBI、TF-A、U-Boot。
- `plat/<platform>/`：平台相关配置和流程，例如设备树、Linux defconfig、平台 README。
- `build/`：所有构建产物，git 忽略。
- `external/`：下载或软链接的外部源码树，git 忽略。
- `cache/`：下载缓存，git 忽略。

架构通用资源通过 `arch/<arch>/resources.json` 声明，平台额外资源可以放在 `plat/<platform>/platform.json` 的 `resources` 字段中。资源默认放在 `external/<arch>/` 下；如果目标目录已经存在，下载步骤会跳过。用户可以手动创建软链接来复用已有源码。

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
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

这里的 `--cross-compile` 是前缀，不包含 `gcc`。脚本会使用 `/path/to/<target-triplet>-gcc`。
架构由所选平台的 `platform.json` 决定，用户不需要单独传入架构参数。

宿主机是 x86 时，不能把宿主机上的 x86 动态库直接拷进目标 initramfs。默认 `apps/hello` 使用静态链接；真实 workload 也应该使用目标架构的 Linux 用户态工具链编译。

平台额外依赖见各平台 README。

## 通用命令

下载资源：

```sh
python3 workload.py fetch --platform <platform>
```

如果本机已经有源码，直接软链接到对应 `external/<arch>/<dest>` 即可：

```sh
mkdir -p external/<platform-arch>
ln -s /path/to/linux external/<platform-arch>/linux
```

检查工具、资源和平台配置：

```sh
python3 workload.py doctor \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

查看构建计划：

```sh
python3 workload.py print-plan \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

一键构建：

```sh
python3 workload.py all \
  --platform <platform> \
  --cross-compile /path/to/<target-triplet>-
```

默认流程：

```text
build-workload -> build-dtb -> build-kernel -> build-firmware
```

分步构建：

```sh
python3 workload.py build-workload --platform <platform> --cross-compile /path/to/<target-triplet>-
python3 workload.py build-dtb      --platform <platform>
python3 workload.py build-kernel   --platform <platform> --cross-compile /path/to/<target-triplet>-
python3 workload.py build-firmware --platform <platform> --cross-compile /path/to/<target-triplet>-
```

平台可以提供兼容别名。例如 RISC-V/XiangShan 使用 `build-opensbi`。

## 添加 Workload

各 workload 的构建、运行和专用约定请直接查看对应的
`apps/<name>/README.md` 或 `apps/<name>/Makefile`。

## 配置扩展

架构资源声明放在：

```text
arch/<arch>/resources.json
```

平台配置放在：

```text
plat/<platform>/platform.json
```

平台若有额外外部资源，也放在 `platform.json` 的 `resources` 字段中。`fetch` 会合并架构资源和平台资源。

常用字段：

- `arch`：平台所属架构。
- `firmware`：平台固件制作类型，例如 `opensbi`、`payload` 或 `tfa`。
- `linux_arch`：Linux Kbuild 使用的 `ARCH` 名称。未设置时默认等于 `arch`。
- `linux_defconfig`：平台使用的 Linux defconfig。
- `dts_generator`：平台使用的 DTS 生成器。

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
python3 workload.py all --platform <platform> --profile hello --cross-compile /path/to/<target-triplet>-
```

profile 默认选择同名的 `apps/<profile>`，同时作为构建输出目录名。需要让输出目录名与
app 名称不同时，再使用 `--workload <app>` 覆盖。

workload 的专用参数统一通过可重复的键值选项传入，由对应 workload 的 Makefile 或构建脚本
解释；主入口不维护 benchmark 参数表：

```sh
python3 workload.py build-workload --platform <platform> --profile <workload> \
  --workload-option key=value \
  --cross-compile /path/to/<target-triplet>-
```

这些选项会同时以 `UNIFIED_WORKLOAD_OPTIONS` JSON 环境变量传给 workload 构建脚本。

平台参数通过统一的键值选项传入，具体可用键由平台 workflow 校验：

```sh
python3 workload.py all --platform <platform> \
  --platform-option harts=4 \
  --platform-option bootargs="console=ttyAMA0 earlycon" \
  --cross-compile /path/to/<target-triplet>-
```

指定并行编译任务数：

```sh
python3 workload.py all --platform <platform> --jobs 16 --cross-compile /path/to/<target-triplet>-
```

只看命令不真正执行：

```sh
python3 workload.py all --platform <platform> --cross-compile /path/to/<target-triplet>- --dry-run
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
