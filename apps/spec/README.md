# SPEC CPU2006/CPU2017 bare-metal workload

`apps/spec` 用于把外部 SPEC CPU2006 或 SPEC CPU2017 benchmark 编译为 AArch64
裸机 workload。
SPEC 源码和输入数据不会复制到仓库中；构建时只读取现有 SPEC 安装目录，并把需要的
源码暂存到 `build/` 下。

当前已在 `qemu-minivirt-aarch64-bare-gcpt` 上完成 CPU2006 `462.libquantum` 的
编译和运行验证。CPU2017 speed 适配使用伪 SPEC 树完成了 C、C++、LTO、参数和多层
输入目录的端到端验证；由于开发环境没有真实 CPU2017 源码，官方子项仍应在源码可用后
逐项验证。

## SPEC 目录

`SPEC_BENCHSPEC` 必须指向 SPEC 安装树中的 `benchspec` 目录。CPU2006 使用
`benchspec/CPU2006/`：

```text
/media/lurker/Newsmy/cpu2006_analyze/benchspec/
└── CPU2006/
    ├── 401.bzip2/
    │   ├── Spec/object.pm
    │   ├── src/
    │   └── data/{test,train,ref}/input/
    ├── 462.libquantum/
    └── ...
```

CPU2017 使用 `benchspec/CPU/`：

```text
/path/to/cpu2017/benchspec/
└── CPU/
    ├── 605.mcf_s/
    │   ├── Spec/object.pm
    │   ├── src/
    │   └── data/{all,test,train,refspeed}/input/
    ├── 631.deepsjeng_s/
    └── ...
```

`SPEC_SUITE=auto` 会先检查 `CPU/<benchmark>`，然后检查
`CPU2006/<benchmark>`。也可以显式设置 `SPEC_SUITE=2006` 或
`SPEC_SUITE=2017`。

对于需要 SPEC 预处理器的 Fortran benchmark，默认从 `SPEC_BENCHSPEC` 的父目录寻找
`bin/specperl` 和 `bin/specpp`。如果实际目录结构不同，可以显式设置 `SPEC_ROOT`。
CPU2017 的 Fortran 或 C/Fortran 混合子项当前明确不支持，元数据阶段会直接报错。
CPU2017 接受 `_s` speed 和 `_r` rate workload。裸机平台每次只运行一个 benchmark
实例并强制 `harts=1`；单实例 `_r` 可用于仿真和性能分析，但不构成正式 SPECrate
多副本测量。适配层通过 `SPEC_AUTO_SUPPRESS_OPENMP` 关闭源码中可选的 OpenMP 路径。

## 构建流程

构建分为两步：

1. `build-workload` 解析 `Spec/object.pm`，暂存源码，生成固定的 `argc/argv` 和嵌入式
   输入文件，然后链接裸机 ELF 和 `bare/payload.bin`。
2. `build-gcpt` 把裸机 payload 放到 `0x40200000`，并在 `0x40000000` 加入 GCPT
   restorer，生成可直接加载的最终 raw 镜像 `gcpt/gcpt.bin`。

不要把 `bare/payload.bin` 直接交给从 `0x40000000` 启动的 mini-virt。它的链接地址是
`0x40200000`，必须使用最终的 `gcpt.bin` 启动。

所有 `SPEC_*` 变量只在 `build-workload` 阶段使用。`build-gcpt` 只封装已经生成的
`bare/payload.bin`，不需要重复传递 benchmark、输入或优化参数。若修改了任何源码编译
参数，必须重新执行 `build-workload`，再执行 `build-gcpt`。

## 最小示例

下面编译执行较快的 CPU2006 `462.libquantum` test workload：

```sh
SPEC_BENCHSPEC=/media/lurker/Newsmy/cpu2006_analyze/benchspec \
SPEC_BENCHMARK=462.libquantum \
SPEC_SIZE=test \
SPEC_ARGS='33 5' \
SPEC_EXTRA_CFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto' \
python3 workload.py build-workload \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile spec \
  --cross-compile /home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-

python3 workload.py build-gcpt \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile spec \
  --cross-compile /home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-
```

CPU2017 C 子项使用相同入口。例如 `605.mcf_s` 的 test invocation：

```sh
SPEC_BENCHSPEC=/path/to/cpu2017/benchspec \
SPEC_SUITE=2017 \
SPEC_BENCHMARK=605.mcf_s \
SPEC_SIZE=test \
SPEC_ARGS='inp.in' \
SPEC_EXTRA_CFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto' \
python3 workload.py build-workload \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile spec \
  --cross-compile /home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-
```

CPU2017 C++ 子项应把同一组优化参数放入 `SPEC_EXTRA_CXXFLAGS`。

### 没有输入文件

“没有输入”需要进一步区分是否仍有命令行参数：

- 不读任何文件且没有参数：设置 `SPEC_EMBED_INPUTS=0`，省略 `SPEC_ARGS` 和
  `SPEC_STDIN`。程序收到 `argc=1`，`argv[0]` 是 `object.pm` 中的可执行文件名。
- 不读任何文件但有数字或选项参数：设置 `SPEC_EMBED_INPUTS=0`，并用 `SPEC_ARGS`
  给出参数。
- 不读文件但程序尝试读取标准输入：未设置 `SPEC_STDIN` 时，fd 0 固定返回 EOF。

没有输入文件、没有运行参数的 CPU2017 C workload 完整模板如下。示例中的
`NNN.name_s` 是占位目录名，必须替换为实际的 CPU2017 speed benchmark 名称：

```sh
SPEC_BENCHSPEC=/path/to/cpu2017/benchspec \
SPEC_SUITE=2017 \
SPEC_BENCHMARK=NNN.name_s \
SPEC_EMBED_INPUTS=0 \
SPEC_ARGS= \
SPEC_STDIN= \
SPEC_EXTRA_CFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto' \
python3 workload.py build-workload \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile spec \
  --cross-compile /home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-

python3 workload.py build-gcpt \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile spec \
  --cross-compile /home/lurker/tools/arm-compiler/bin/aarch64-none-linux-gnu-
```

如果程序不读文件，但需要参数，例如 `--iterations 1000`，只需在上面的
`build-workload` 环境中增加：

```sh
SPEC_ARGS='--iterations 1000'
```

`SPEC_EMBED_INPUTS=0` 时，`SPEC_SIZE`、`SPEC_INPUT_DIR` 和 `SPEC_INPUT_DIRS` 不参与输入
打包，`SPEC_STDIN` 必须保持为空。这个模式也允许 benchmark 目录完全没有 `data/`
子目录。

主要产物为：

```text
build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/workload/spec
build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/bare/payload.bin
build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/gcpt/gcpt.bin
build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/run-qemu.sh
```

## QEMU 运行

平台默认使用 4 GiB RAM。使用 Neoverse N1 运行最终镜像：

```sh
/home/lurker/workspace/rt-workspace/arm64-simpoint/arm-qemu/build/qemu-system-aarch64 \
  -machine mini-virt \
  -cpu neoverse-n1 \
  -smp 1 \
  -m 4G \
  -nographic \
  -kernel build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/gcpt/gcpt.bin
```

`462.libquantum` 的成功输出应包含：

```text
N = 33, 31 qubits required
Random seed: 5
33 = 11 * 3
```

当前裸机 `_exit` 会进入 `wfe` 驻留，因此程序返回后 QEMU 不会自动退出。生产切片流程
应使用相应的 simtrap 或外部运行控制结束模拟。

## 构建参数

构建参数分为三层：`workload.py` 命令行参数选择平台和构建目标，`SPEC_*` 环境变量选择
benchmark 及其固定 invocation，编译器 flags 控制生成代码。不要把不同层中名称相似的
参数当成等价接口。

### workload.py 参数

| 参数 | 本适配中的用法 |
| --- | --- |
| `build-workload` | 编译 benchmark，生成 ELF 和 `bare/payload.bin` |
| `build-gcpt` | 封装现有 payload，生成最终 `gcpt/gcpt.bin` |
| `--arch aarch64-bare` | 必须，选择 AArch64 裸机运行时和 newlib |
| `--platform qemu-minivirt-aarch64-bare-gcpt` | 必须，选择当前内存、UART、链接地址和 GCPT 布局 |
| `--profile spec` | 必须，选择 `apps/spec`，同时决定产物目录 |
| `--cross-compile <prefix>` | 必须，工具链前缀必须以 `-` 结尾，不是工具链目录 |
| `--jobs N` | 可选，控制 newlib、GCPT 等支持该参数的构建步骤；当前 `apps/spec` Makefile 不会因此获得 `-j`，也不改变 benchmark 线程数 |
| `--harts 1` | 可选；平台默认已经是 1，其他值会报错 |
| `--workload spec` | 与 `--profile spec` 中的 workload 选择重复，正常使用时不要再设置 |
| `--workload-dir DIR` | 覆盖 `apps/spec`，本适配正常使用时不要设置 |
| `--cflags FLAGS` | 平台级附加 workload C/C++ flags；当前平台会把它同时并入 `BARE_CFLAGS` 和 `BARE_CXXFLAGS` |
| `--ldflags FLAGS` | 平台级附加 workload 链接 flags；当前平台会把它并入 `BARE_LDFLAGS` |

对 SPEC workload，优先使用后文的 `SPEC_EXTRA_CFLAGS`、`SPEC_EXTRA_CXXFLAGS` 和
`SPEC_EXTRA_LDFLAGS`。`--cflags`/`--ldflags` 是更宽泛的平台接口，只应在确实需要让
benchmark 与 SPEC 运行时辅助代码使用同一 ABI 或代码模型选项时使用。它们不会改变
已经单独编译的 startup、syscalls 或 newlib。两个选项都可以重复传入；同一个 flag 不要
同时放入 `--cflags`/`--ldflags` 和 `SPEC_EXTRA_*`。

### benchmark 选择

| 变量 | 默认值 | 正确用法 |
| --- | --- | --- |
| `SPEC_BENCHSPEC` | 无 | 必填，指向包含 `CPU2006/` 或 `CPU/` 的 `benchspec` 目录 |
| `SPEC_BENCHMARK` | `401.bzip2` | benchmark 完整目录名，例如 `605.mcf_s` 或 `505.mcf_r` |
| `SPEC_SUITE` | `auto` | 优先自动识别；同名目录可能产生歧义时显式设为 `2006` 或 `2017` |
| `SPEC_ROOT` | `SPEC_BENCHSPEC` 的父目录 | 只用于寻找 CPU2006 Fortran 的 `bin/specperl`/`bin/specpp` |

`SPEC_BENCHSPEC` 是套件级目录，不能指向单个 benchmark。正确值是
`/path/to/cpu2017/benchspec`，不是 `/path/to/cpu2017/benchspec/CPU/605.mcf_s`。

### invocation 与输入

| 变量 | 默认值 | 正确用法 |
| --- | --- | --- |
| `SPEC_ARGS` | 空 | 固定的 `argv[1:]`；使用 shell 形式解析，但不会自动读取 `object.pm` 的 invocation |
| `SPEC_STDIN` | 空 | 映射到 fd 0 的嵌入文件相对路径；必须能在最终输入集合中找到 |
| `SPEC_SIZE` | `test` | 只选择默认输入目录；CPU2006 使用 `test/train/ref`，CPU2017 speed 使用 `test/train/refspeed` |
| `SPEC_EMBED_INPUTS` | `1` | `1` 打包输入文件；完全不读文件时必须显式设为 `0` |
| `SPEC_INPUT_DIRS` | 默认输入目录列表 | 多个目录的有序空格分隔列表，后面的目录覆盖前面的同名相对路径 |
| `SPEC_INPUT_DIR` | 无 | 旧的单目录覆盖接口；只需要一个自定义输入目录时使用 |

默认 `SPEC_INPUT_DIRS` 按顺序包含存在的 `data/all/input`，以及
`data/$(SPEC_SIZE)/input`。当 `SPEC_EMBED_INPUTS=1` 时，传入的每个目录都必须存在；目录
可以为空，但至少要有一个输入目录。自定义多目录时使用 `SPEC_INPUT_DIRS`：

```sh
SPEC_INPUT_DIRS='/path/to/common/input /path/to/test/input'
```

只覆盖为一个目录时使用：

```sh
SPEC_INPUT_DIR=/path/to/custom/input
```

不要同时设置 `SPEC_INPUT_DIR` 和 `SPEC_INPUT_DIRS`。这些变量按空格拆分目录，因此输入
目录本身不要包含空格。

`SPEC_ARGS` 使用 Python `shlex` 规则拆分。整个值通常用单引号保护；参数本身含空格时，
在值内部使用双引号：

```sh
SPEC_ARGS='--mode fast "input file.dat" 100'
```

这会产生四个参数：`--mode`、`fast`、`input file.dat`、`100`。`SPEC_SIZE` 只决定打包
哪个输入目录，不会自动选择参数、stdin 或多次 invocation。一个镜像只能固化一组
`SPEC_ARGS` 和 `SPEC_STDIN`。

### 编译与链接变量

| 变量 | 作用范围 | 何时设置 |
| --- | --- | --- |
| `SPEC_EXTRA_CFLAGS` | 仅 benchmark 的 `.c` 源码 | C benchmark，或含 C 源码的混合 C/C++ benchmark |
| `SPEC_EXTRA_CXXFLAGS` | 仅 benchmark 的 `.C/.cc/.cpp/.cxx` 源码 | C++ benchmark，或含 C++ 源码的混合 benchmark |
| `SPEC_EXTRA_FFLAGS` | 仅 benchmark 的 Fortran 源码 | 仅 CPU2006；CPU2017 Fortran 不支持 |
| `SPEC_EXTRA_LDFLAGS` | benchmark 最终链接 | LTO、链接器优化、链接脚本参数或额外库搜索路径 |
| `SPEC_OPTIMIZE` | 非裸机构建的默认优化等级 | 当前 `aarch64-bare` 流程不使用，不要设置 |

名称相近的 `BARE_*`、`SPEC_PLATFORM_*`、`SPEC_COMMON_*`、`SPEC_COMPAT_CFLAGS` 和
`SPEC_BENCH_*` 都是平台或元数据生成的内部变量，不是用户配置入口。正常使用时只设置
上表中的 `SPEC_EXTRA_*`，不要通过环境变量覆盖这些内部值。

不要直接设置 `CFLAGS`、`CXXFLAGS`、`FFLAGS`、`LDFLAGS` 或 `LDLIBS`。这些是适配层内部
合成变量，平台启动文件、newlib、SPEC 兼容参数和语言运行库都依赖其固定组合。

实际顺序如下，右侧同类选项通常覆盖左侧选项：

```text
C 编译:
  平台 BARE_CFLAGS
  -> CPU2006/CPU2017 公共 flags
  -> benchmark 公共兼容 flags
  -> SPEC_EXTRA_CFLAGS
  -> benchmark C 专用兼容 flags

C++ 编译:
  平台 BARE_CXXFLAGS
  -> CPU2006/CPU2017 公共 flags
  -> benchmark 公共兼容 flags
  -> SPEC_EXTRA_CXXFLAGS
  -> benchmark C++ 专用兼容 flags

链接:
  平台 BARE_LDFLAGS
  -> 裸机 I/O wrap flags
  -> benchmark 必需链接 flags
  -> SPEC_EXTRA_LDFLAGS
  -> benchmark 必需库
  -> C++/Fortran 语言运行库
  -> newlib libc/libm/libgcc
```

benchmark 专用兼容 flags 放在用户优化参数之后。例如 `600.perlbench_s` 会在用户的
`-Ofast` 之后追加 `-fno-unsafe-math-optimizations -fno-finite-math-only`，不能用
`SPEC_EXTRA_CFLAGS` 再覆盖这些正确性要求。

### 自动提供的 flags

正常构建不需要重复添加下表中的选项。它们由平台或 SPEC 适配层自动提供：

| 来源 | 自动提供的主要选项 | 说明 |
| --- | --- | --- |
| AArch64 裸机平台 | `-O3 -march=armv9-a -ffreestanding -fno-pic -fno-pie -fno-stack-protector -ffunction-sections -fdata-sections` | `-O3` 是默认优化；用户后置的 `-Ofast` 会覆盖优化等级 |
| CPU2006 公共层 | `-DSPEC_CPU -DNDEBUG -D_FILE_OFFSET_BITS=64 -DSPEC_CPU_LP64 -fno-strict-aliasing` | CPU2006 的 C/C++ 源码自动使用 |
| CPU2017 公共层 | `-DSPEC -DNDEBUG -D_FILE_OFFSET_BITS=64 -DSPEC_LP64 -DSPEC_AUTO_SUPPRESS_OPENMP -fno-strict-aliasing` | 所有 CPU2017 源码自动使用，并关闭可选 OpenMP 路径 |
| CPU2017 语言层 | C 使用 `-std=c99`，C++ 使用 `-std=c++03` | 不要用 `SPEC_EXTRA_*` 重复设置相同标准，除非已确认源码兼容其他标准 |
| 裸机链接层 | `-nostdlib -static -no-pie`、链接脚本、`--gc-sections`、`libc/libm/libgcc` | C++/Fortran 语言运行库按源码语言自动追加 |

如果不要求特定微架构、激进浮点优化或 LTO，可以完全省略 `SPEC_EXTRA_CFLAGS`、
`SPEC_EXTRA_CXXFLAGS` 和 `SPEC_EXTRA_LDFLAGS`，此时 benchmark 使用平台默认的
`-O3 -march=armv9-a`。设置 `-mcpu=...` 后，适配层只会在对应语言的
`SPEC_EXTRA_CFLAGS` 或 `SPEC_EXTRA_CXXFLAGS` 中检测它并移除冲突的默认 `-march`。

### 推荐优化组合

当前常用优化串中各选项的含义如下：

| flag | 含义与注意事项 |
| --- | --- |
| `-mcpu=neoverse-n1` | 选择 N1 可用指令并针对 N1 调度；适配层会移除该语言的平台 `-march=...` |
| `-Ofast` | 激进优化并放宽部分语言/浮点语义；必须使用 SPEC 输出校验确认结果 |
| `-fomit-frame-pointer` | 释放 frame pointer 寄存器；会降低部分调试和回溯能力 |
| `-g1` | 保留最少调试信息，主要用于符号定位，通常不改变执行代码 |
| `-flto` | 启用链接时优化；编译阶段和最终链接阶段必须同时设置 |

纯 C benchmark：

```sh
SPEC_EXTRA_CFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto'
```

纯 C++ benchmark：

```sh
SPEC_EXTRA_CXXFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto'
```

混合 C/C++ benchmark 必须给两种源码都设置编译参数，链接参数仍只设置一次：

```sh
SPEC_EXTRA_CFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_CXXFLAGS='-mcpu=neoverse-n1 -Ofast -fomit-frame-pointer -g1 -flto' \
SPEC_EXTRA_LDFLAGS='-flto'
```

`-mcpu` 应放在对应的 `SPEC_EXTRA_CFLAGS`/`SPEC_EXTRA_CXXFLAGS` 中。不要改用
`--cflags=-mcpu=...`，因为当前冲突消解只根据 `SPEC_EXTRA_*` 移除平台默认的
`-march=...`。不使用 LTO 时，三种组合都应同时删除编译参数和链接参数中的 `-flto`，
不能只删一侧。

`SPEC_EXTRA_LDFLAGS` 出现在目标文件之前，适合 `-flto`、`-L/path/to/lib` 和
`-Wl,...` 这类全局链接选项，不适合直接追加普通静态库 `-lfoo`，否则可能因归档解析
顺序而出现未定义符号。当前已确认的 benchmark 库由适配层自动放在目标文件之后。若真实
源码暴露新的静态库依赖，应先把它加入该 benchmark 的内置依赖表，再构建；不要重复添加
适配层已经提供的 `-lc`、`-lm`、`-lgcc`、C++ runtime 或 SPEC 树内组件。

## 参数和输入文件

裸机环境没有命令行和宿主文件系统，因此构建阶段会生成固定运行配置：

- `SPEC_ARGS` 被转换为静态 `argc/argv`，并通过 linker wrap 传给 benchmark 的 `main`。
- `data/all/input` 和 `SPEC_SIZE` 对应输入目录中的普通文件会被递归打包进 ELF 的
  只读数据段；规模输入中的同名文件覆盖 `all` 输入。
- benchmark 打开输入文件时使用相对路径，例如 `dryer.jpg` 或 `data/file.in`。
- 路径开头的一个或多个 `./` 会被忽略。
- `SPEC_STDIN=su3imp.in` 会把该嵌入文件映射为标准输入。

常见组合如下：

| benchmark 运行方式 | 必须设置 | 必须保持为空或省略 |
| --- | --- | --- |
| 无文件、无参数 | `SPEC_EMBED_INPUTS=0` | `SPEC_ARGS`、`SPEC_STDIN` |
| 无文件、有参数 | `SPEC_EMBED_INPUTS=0`、`SPEC_ARGS` | `SPEC_STDIN` |
| 默认输入目录，文件名通过 argv 传入 | `SPEC_SIZE`、`SPEC_ARGS` | `SPEC_STDIN`，除非程序也读 stdin |
| 默认输入目录，只从 stdin 读取文件 | `SPEC_SIZE`、`SPEC_STDIN` | `SPEC_ARGS`，除非程序另有参数 |
| 默认输入目录，argv 文件和 stdin 同时使用 | `SPEC_SIZE`、`SPEC_ARGS`、`SPEC_STDIN` | 无 |
| 单个自定义输入目录 | `SPEC_INPUT_DIR`，再按 invocation 设置 `SPEC_ARGS`/`SPEC_STDIN` | `SPEC_INPUT_DIRS`；`SPEC_SIZE` 不再选择目录 |
| 多个自定义输入目录 | `SPEC_INPUT_DIRS`，再按 invocation 设置 `SPEC_ARGS`/`SPEC_STDIN` | `SPEC_INPUT_DIR`；`SPEC_SIZE` 不再选择目录 |

只要需要嵌入文件，就保持默认的 `SPEC_EMBED_INPUTS=1`，不必显式重复设置。

例如构建使用标准输入的 benchmark：

```sh
SPEC_BENCHMARK=433.milc \
SPEC_SIZE=test \
SPEC_STDIN=su3imp.in \
...
```

输入文件只在构建时读取。SPEC 安装树不会被修改；暂存源码、生成的文件索引和输入
blob 位于：

```text
build/plat/<platform>/<profile>/workload/obj/spec/<benchmark>/
```

## 简化文件 I/O

`bare_io.c` 提供面向 benchmark 的最小文件描述符映射：

- 嵌入文件支持只读 `open`、`read`、`lseek`、`fstat` 和 `close`。
- 标准输入可以映射到一个嵌入文件；未配置时读取 fd 0 返回 EOF。
- 以写模式创建或打开的文件是 sink：写操作报告成功，但数据会被丢弃。
- fd 1 和 fd 2 仍写入平台 UART。
- 不存在的只读文件返回 `ENOENT`。

该实现不提供目录遍历、持久化文件、宿主文件访问或完整 POSIX 文件系统语义。依赖这些
行为的 benchmark 需要继续扩展适配层。

## 子项元数据

`metadata.py` 从每个 benchmark 的 `Spec/object.pm` 读取源码列表、语言和可执行文件名。
CPU2006 使用适配层中的兼容参数表；CPU2017 使用内置的 C/C++ 子项兼容参数，并继续
读取 `object.pm` 中可选的 `bench_flags`、`bench_cflags`、`bench_cxxflags`、
`bench_ldflags` 和 `need_math` 作为追加参数。源码只会被复制到构建目录，便于在不修改
SPEC 安装树的情况下编译。

CPU2017 当前支持以下不含 Fortran 的 speed 子项：

```text
600.perlbench_s   602.gcc_s        605.mcf_s       619.lbm_s
620.omnetpp_s     623.xalancbmk_s  625.x264_s      631.deepsjeng_s
638.imagick_s     641.leela_s      644.nab_s       657.xz_s
```

`631.deepsjeng_s` 会自动定义 `BIG_MEMORY`，不会沿用 rate 版本的 `SMALL_MEMORY`。
`600.perlbench_s` 在使用 `-Ofast` 时会自动追加
`-fno-unsafe-math-optimizations -fno-finite-math-only`，避免已知的校验错误。

## 子项依赖

裸机平台始终链接 newlib `libc`、`libm` 和 `libgcc`；C++ workload 额外链接静态
`libstdc++`、`libsupc++` 和 `libgcc_eh`。speed C/C++ 子项的其余依赖如下：

| 子项 | 编译或链接要求 | SPEC 树内自带组件 | 当前运行风险 |
| --- | --- | --- | --- |
| `600.perlbench_s` | `libm`、`-z muldefs` | Perl 和 CPAN 模块 | 文件接口复杂，需真实源码验证 |
| `602.gcc_s` | `-z muldefs` | GCC、mini-gmp、spec_qsort | 临时文件及 POSIX 接口较多 |
| `605.mcf_s` | 无额外库 | spec_qsort | 低，建议优先验证 |
| `619.lbm_s` | `libm` | 无 | 低，建议优先验证 |
| `620.omnetpp_s` | C++ runtime | OMNeT++ 模型代码 | 输出文件会被丢弃 |
| `623.xalancbmk_s` | C++ runtime | Xalan、Xerces | 文件接口复杂；不需要外部 pthread/iconv |
| `625.x264_s` | `libm`、`-fcommon` | x264、ldecod | 两遍编码需要保留中间 stats，当前 sink 不支持 |
| `631.deepsjeng_s` | C++ runtime、`BIG_MEMORY` | 无 | 低，建议优先验证 |
| `638.imagick_s` | `libm` | 精简 ImageMagick | 大输入，输出文件会被丢弃 |
| `641.leela_s` | C++ runtime | 精简 Boost | 低，建议优先验证 |
| `644.nab_s` | `libm` | regexp、specrand | 低，建议优先验证 |
| `657.xz_s` | 串行构建 | liblzma、SHA-2 | 内存占用较大，OpenMP 已关闭 |

因此当前不需要下载额外第三方库，也不链接 `libpthread`、`libgomp`、`libdl` 或
`libiconv`。主要缺口是系统调用和可写内存文件，而不是链接库。单个 SPEC 子项可能有
多个 invocation；一个裸机镜像只对应一组固定的 `SPEC_ARGS`/`SPEC_STDIN`，需要分别构建。

切换 `SPEC_BENCHMARK` 时会使用独立的对象目录。若在同一 profile 下修改编译参数并希望
强制全量重编，删除对应目录后重新执行 `build-workload`：

```sh
rm -rf build/plat/qemu-minivirt-aarch64-bare-gcpt/spec/workload/obj/spec/462.libquantum
```

## 参考

- [SPEC CPU2017 suites and benchmark list](https://spec.org/cpu2017/Docs/overview.html)
- [SPEC CPU2017 Make Variables](https://spec.org/cpu2017/Docs/makevars.html)
- [SPEC CPU2017 `runcpu` directory layout](https://spec.org/cpu2017/Docs/runcpu.html)
- [OpenXiangShan CPU2017LiteWrapper](https://github.com/OpenXiangShan/CPU2017LiteWrapper)
