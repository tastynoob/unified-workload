# QEMU Mini-Virt AArch64 GCPT Platform

`qemu-minivirt-aarch64-gcpt` is the checkpoint-oriented variant of
`qemu-minivirt-aarch64`.

Current boot path:

```text
gcpt.bin -> AArch64 restorer -> embedded AArch64 payload -> Linux kernel -> /init
```

The AArch64 GCPT layer disables interrupts, initializes the PL011 UART by
itself, checks for checkpoint metadata, and falls back to the normal payload when
no checkpoint is present.

## Layout

```text
0x40000000: gcpt boot wrapper
0x40100000: checkpoint metadata or default core-0 register data
0x40200000: embedded AArch64 payload
0x40400000: Linux Image inside the embedded payload
```

The first 2 MiB are reserved in the generated DTB:

```text
reserved-memory gcpt@40000000 size 0x200000 no-map
```

Within that reserved range, the current split is:

```text
0x40000000..0x400fffff: restorer window, 1 MiB
0x40100000..0x401fffff: checkpoint metadata/default core data window, 1 MiB
```

The default per-core register stride is 1 MiB, matching the RISC-V
libcheckpoint style. The current fixed AArch64 register layout uses up to
`0x70050` bytes per core when all present blocks are included, or `0x6210` bytes
for the base state through FPSIMD.

This 2 MiB reservation does not support 128 cores. With the current 1 MiB
per-core stride, a 128-core checkpoint needs:

```text
0x100000 restorer window
0x007000 metadata for header + 128 per-core layouts
0x8000000 register stride area for 128 cores
= 0x8107000 bytes before payload
```

Rounded to the existing 2 MiB alignment, the payload would need to move from
`0x40200000` to at least `0x48200000`. If the future format uses the current
compact `0x70050` bytes of actual full register data per core instead of the
1 MiB stride, 128 cores need `0x3909800` bytes before alignment, rounded to
`0x3a00000`, so the payload would need to start at `0x43a00000`.

## External Resource

The AArch64 checkpoint source is fetched as a platform resource:

```sh
python3 workload.py fetch libcheckpoint-for-aarch64 \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64-gcpt
```

It will be placed under:

```text
external/aarch64/libcheckpoint-for-aarch64
```

If you already have a checkout, a symlink at that path works as well. The
current platform only requires that resource to provide the minimal boot payload
build interface documented by the resource itself.

## Build

```sh
export AARCH64_CROSS=/path/to/aarch64-none-linux-gnu-

python3 workload.py all \
  --arch aarch64 \
  --platform qemu-minivirt-aarch64-gcpt \
  --cross-compile "$AARCH64_CROSS"
```

Equivalent split build:

```sh
python3 workload.py build-workload --arch aarch64 --platform qemu-minivirt-aarch64-gcpt --cross-compile "$AARCH64_CROSS"
python3 workload.py build-dtb      --arch aarch64 --platform qemu-minivirt-aarch64-gcpt
python3 workload.py build-kernel   --arch aarch64 --platform qemu-minivirt-aarch64-gcpt --cross-compile "$AARCH64_CROSS"
python3 workload.py build-gcpt     --arch aarch64 --platform qemu-minivirt-aarch64-gcpt --cross-compile "$AARCH64_CROSS"
```

## Run

```sh
build/plat/qemu-minivirt-aarch64-gcpt/hello/run-qemu.sh
```

Expected hello output:

```text
hello
hanging
```

## Key Outputs

```text
build/plat/qemu-minivirt-aarch64-gcpt/hello/payload/aarch64-payload.bin
build/plat/qemu-minivirt-aarch64-gcpt/hello/gcpt/gcpt.bin
build/plat/qemu-minivirt-aarch64-gcpt/hello/gcpt/layout.txt
build/plat/qemu-minivirt-aarch64-gcpt/hello/run-qemu.sh
```
