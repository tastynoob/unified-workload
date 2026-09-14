# any

`any` 将已编译的目标架构 Linux ELF 和运行所需文件打包进 initramfs。外部 ELF
直接安装为 `/init`，运行过程中不会创建 launcher 或额外进程。

## Profiling wrapper

外部 ELF 应在最终链接时加入本目录的 `wrap_main.c`，并使用
`-Wl,--wrap=main`。wrapper 在真实 `main()` 前发出 `PROFILE_START`，在其返回或
调用 `exit()` 时发出 `PROFILE_STOP`：

```sh
TARGET_CC=/path/to/aarch64-linux-gnu-gcc
PLATFORM=qemu-minivirt-aarch64-gcpt

$TARGET_CC -O2 -fno-lto \
  -I../../plat/$PLATFORM/include \
  -c wrap_main.c -o wrap_main.o

$TARGET_CC -static -o benchmark \
  benchmark.o wrap_main.o -Wl,--wrap=main
```

使用 LTO 编译 benchmark 时，wrapper 仍应使用 `-fno-lto` 单独编译。实际链接命令
可以由各 benchmark 在仓库内的小型构建脚本管理。参数、工作目录和标准输入也应由
该 benchmark 的编译期适配层确定；`any` 只负责打包，不模拟命令启动过程。

## 打包参数

| 参数 | 含义 |
| --- | --- |
| `--any-elf PATH` | 必填，安装为 `/init` 的目标架构 Linux ELF |
| `--any-file HOST=GUEST` | 文件或目录映射，可重复；guest 路径必须为绝对路径 |

目录映射会递归保留普通文件、目录和相对符号链接。动态 ELF 所需的解释器和共享库
也必须通过 `--any-file` 显式打包；用于仿真 workload 时优先使用静态 ELF。

例如：

```sh
python3 workload.py all \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64-gcpt \
  --profile any \
  --cross-compile /path/to/aarch64-linux-gnu- \
  --any-elf /path/to/benchmark \
  --any-file /path/to/input.dat=/input.dat
```

对同一平台持续使用相同的 `--build-dir` 和 `--profile any`，Linux、OpenSBI 和其他
固件对象会增量复用；更换 ELF 或输入文件后只重新生成 initramfs 及依赖它的最终镜像。
