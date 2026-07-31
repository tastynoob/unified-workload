# QEMU Mini-Virt AArch64 GCPT Platform

`qemu-minivirt-aarch64-gcpt` is the checkpoint-oriented variant of
`qemu-minivirt-aarch64`.

Current boot path:

```text
gcpt.bin -> AArch64 restorer -> embedded AArch64 payload -> Linux kernel -> /init
```

The AArch64 GCPT boot wrapper checks for snapshot magic before entering the C
restorer. Without a checkpoint it branches directly to the normal payload. The
successful restore path stays silent; PL011 is initialized only for error
messages. Restore failure halts in the wrapper instead of booting the payload.

## Layout

```text
0x40000000: gcpt boot wrapper
0x40100000: streaming checkpoint snapshot
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
0x40100000..0x401fffff: checkpoint metadata/snapshot window, 1 MiB
```

The AArch64 checkpoint layout is a single `a64_snapshot_header` followed by
compact raw register blocks. Without `A64_CPT_SNAPSHOT_MAGIC` at `0x40100000`,
the restorer boots the embedded payload normally.

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
