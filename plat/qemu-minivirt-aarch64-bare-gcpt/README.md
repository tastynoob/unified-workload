# QEMU mini-virt AArch64 bare-metal GCPT

This platform builds an Armv9-A freestanding workload and wraps it with
`libcheckpoint-for-aarch64`. It is separate from the `aarch64` architecture,
whose platforms continue to build and boot Linux.

The boot wrapper enters the workload at EL1. The runtime installs a minimal
identity map that marks RAM as Normal WB memory and the low MMIO region as
Device-nGnRnE, then initializes the stack and BSS. Console output writes only
to the PL011 data register. It does not configure the GIC, timer interrupts,
architectural counters, or UART control registers. The CoreMark timing hooks
return the fixed value `1`.

For the fixed-iteration CoreMark profile, `start_time` and `stop_time`
delimit the benchmark loop. `stop_time` sends PROFILE_STOP followed by
GOOD_TRAP, so CoreMark's elapsed-time validation and result printing are not
part of the workload. Performance is taken from simulator IPC.

## Resources

newlib and the checkpoint restorer are fetched under `external/aarch64-bare`:

```sh
python3 workload.py fetch \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt
```

For a network that requires the local proxy wrapper:

```sh
proxychains4 -q python3 workload.py fetch \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt
```

newlib is built for the `aarch64-none-elf` ABI. The build accepts an AArch64
freestanding-capable cross compiler through `--cross-compile`; a native
`aarch64-none-elf` toolchain is preferred.

## Build

```sh
python3 workload.py all \
  --arch aarch64-bare \
  --platform qemu-minivirt-aarch64-bare-gcpt \
  --profile hello \
  --cross-compile /path/to/aarch64-none-elf-
```

The final raw image is:

```text
build/plat/qemu-minivirt-aarch64-bare-gcpt/hello/gcpt/gcpt.bin
```

Run it with:

```sh
QEMU_SYSTEM_AARCH64=/path/to/qemu-system-aarch64 \
  build/plat/qemu-minivirt-aarch64-bare-gcpt/hello/run-qemu.sh
```

## Checkpoint

The QEMU checkpoint options are the same as for the Linux GCPT platform. For
example, this creates a CoreMark checkpoint with a 100,000-instruction warmup:

```sh
qemu-system-aarch64 \
  -icount shift=0,sleep=off \
  -machine mini-virt,checkpoint-mode=SimpointCheckpoint,cutpoints=1000000,warmup-interval=100000,checkpoint-dir=/tmp/a64-bare-cpt \
  -cpu max -smp 1 -m 1024M -nographic \
  -kernel build/plat/qemu-minivirt-aarch64-bare-gcpt/coremark/gcpt/gcpt.bin
```

Restore the resulting compressed raw image directly:

```sh
qemu-system-aarch64 \
  -icount shift=0,sleep=off \
  -machine mini-virt -cpu max -smp 1 -m 1024M -nographic \
  -kernel /tmp/a64-bare-cpt/1000000/_1000000_warmup_100000_cpt_900000_.bin.zst
```

CoreMark timing is deliberately fixed at `1`; use simulator IPC and
instruction counts for slice measurement.

## Memory layout

```text
0x40000000..0x400fffff  checkpoint restorer
0x40100000..0x401fffff  streaming snapshot window
0x40200000..0x7fefffff  bare workload text/data/heap
0x7ff00000..0x7fffffff  runtime stack
```
