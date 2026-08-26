# SPEC CPU Workload

`apps/spec` 将外部 SPEC CPU2006 或 CPU2017 的单个 C/C++ benchmark 编译成
unified-workload 的 Linux `/init` workload。SPEC 源码保持只读，构建时复制到
`build/` 下的临时目录；Fortran 或 C/Fortran 混合 benchmark 在 metadata 阶段直接拒绝。

## 输入目录

`SPEC_BENCHSPEC` 指向包含 `CPU2006/` 或 `CPU/` 的 `benchspec` 目录：

```text
/path/to/cpu2017/benchspec/
└── CPU/
    └── 505.mcf_r/
        ├── Spec/object.pm
        ├── src/
        └── data/refrate/input/
```

主要选择变量：

| 变量 | 说明 |
| --- | --- |
| `SPEC_BENCHSPEC` | 必填，suite 级 `benchspec` 目录 |
| `SPEC_SUITE` | `auto`、`2006` 或 `2017`，默认 `auto` |
| `SPEC_BENCHMARK` | benchmark 目录名，例如 `505.mcf_r` |
| `SPEC_SIZE` | 输入目录名，例如 `test`、`train`、`ref`、`refrate` 或 `refspeed` |
| `SPEC_ARGS` | 固定传给 benchmark 的 `argv[1:]` |
| `SPEC_INPUT_DIR` | 可选的单个自定义输入目录 |

`data/all/input`（若存在）会先复制，再复制 `data/<SPEC_SIZE>/input`；后者同名文件
覆盖前者。也可以用 `SPEC_INPUT_DIR` 指定自定义目录。输入文件会被递归放入最终
initramfs，benchmark 通过普通相对路径打开它们。

没有输入文件的 benchmark 只需不提供有效的输入目录；如果仍需要命令行参数，照常设置
`SPEC_ARGS`。例如没有文件但需要一个迭代次数：

```sh
SPEC_SIZE=none SPEC_ARGS='1000'
```

## 编译参数

Makefile 先使用 `SPEC_OPTIMIZE` 作为 C/C++ 的共同优化参数，默认是 `-O3`，再追加：

| 变量 | 作用 |
| --- | --- |
| `SPEC_EXTRA_CFLAGS` | 仅 C 源文件 |
| `SPEC_EXTRA_CXXFLAGS` | 仅 C++ 源文件 |
| `SPEC_EXTRA_LDFLAGS` | 最终链接 |
| `SPEC_CROSS_COMPILE` | 仅 SPEC workload 的工具链前缀；未设置时使用 `--cross-compile` |

常用的统一优化组合：

```sh
SPEC_OPTIMIZE='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto'
```

C 和 C++ 混合 benchmark 可分别追加对应的 `SPEC_EXTRA_*FLAGS`。SPEC 适配层会从
`Spec/object.pm` 读取源码列表、语言、可执行文件名和 benchmark 必需的兼容参数；不要
直接覆盖内部的 `CFLAGS`、`CXXFLAGS` 或 `LDFLAGS`。

## 构建示例

下面以 CPU2017 `505.mcf_r` 的 test 输入为例。命令只构建一个 workload 实例，不能用于
正式 SPECrate 多副本计分：

```sh
SPEC_BENCHSPEC=/path/to/cpu2017/benchspec \
SPEC_SUITE=2017 \
SPEC_BENCHMARK=505.mcf_r \
SPEC_SIZE=test \
SPEC_ARGS='inp.in 1' \
SPEC_OPTIMIZE='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto' \
python3 workload.py build-workload \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64-gcpt \
  --profile spec \
  --cross-compile /path/to/aarch64-none-linux-gnu-
```

`all` 命令会继续构建 DTB、Linux kernel、payload 和最终 GCPT 镜像：

```sh
python3 workload.py all \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64-gcpt \
  --profile spec \
  --cross-compile /path/to/aarch64-none-linux-gnu-
```

如果 Linux kernel 的 Kbuild 输出需要放到其他磁盘，设置 `LINUX_KBUILD_DIR`；最终
`Image` 和 initramfs 仍会复制回 unified-workload 的 build 目录，供后续 payload/GCPT
步骤使用。

## 运行参数

构建产物中的 SPEC workload 被安装为 `/init`。`SPEC_ARGS` 在构建时转换为固定的
`argc/argv`，因此镜像启动时不需要额外的命令行。输入文件同样在构建时打包，运行时不
依赖宿主文件系统。

当前适配层只负责单个 C/C++ benchmark 的编译和 Linux initramfs 集成；依赖 Fortran、
多进程、动态装载或未提供的特殊系统调用的子项不会被自动转换。
