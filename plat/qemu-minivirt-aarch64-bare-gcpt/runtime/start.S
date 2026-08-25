.section .text.boot, "ax"
.global _start
.extern __bss_start
.extern __bss_end
.extern __libc_init_array
.extern __libc_fini_array
.extern __stack_top
.extern main
.extern _exit

_start:
    msr daifset, #0xf
    isb

    mrs x0, CurrentEL
    lsr x0, x0, #2
    cmp x0, #3
    b.eq enter_from_el3
    cmp x0, #2
    b.eq enter_from_el2
    cmp x0, #1
    b.eq setup_el1
    b halt

enter_from_el3:
    /* Non-secure AArch64 EL2 with HVC and pointer authentication enabled. */
    mov x6, #0x501
    movk x6, #0x3, lsl #16
    mov x7, xzr
    mov x9, xzr

    mrs x8, id_aa64pfr0_el1
    ubfx x10, x8, #32, #4
    cbz x10, no_el3_sve
    orr x7, x7, #(1 << 8)
    orr x9, x9, #1
no_el3_sve:

    mrs x8, id_aa64pfr1_el1
    ubfx x10, x8, #8, #4
    cmp x10, #2
    b.lo no_el3_mte
    orr x6, x6, #(1 << 26)
no_el3_mte:
    mrs x8, id_aa64mmfr0_el1
    ubfx x10, x8, #56, #4
    cbz x10, no_el3_fgt
    orr x6, x6, #(1 << 27)
no_el3_fgt:

    mrs x8, id_aa64mmfr1_el1
    ubfx x10, x8, #40, #4
    cbz x10, no_el3_hcx
    orr x6, x6, #(1 << 38)
no_el3_hcx:

    mrs x8, S3_0_C0_C7_3
    ubfx x10, x8, #0, #4
    cbz x10, no_el3_tcr2
    orr x6, x6, #(1 << 43)
no_el3_tcr2:
    ubfx x10, x8, #8, #4
    cbz x10, no_el3_s1pie
    orr x6, x6, #(1 << 45)
no_el3_s1pie:

    msr scr_el3, x6
    msr cptr_el3, x7
    isb

    tbz x9, #0, done_el3_sve
    mov x8, #0xf
    msr S3_6_C1_C2_0, x8
done_el3_sve:
    adr x0, enter_from_el2
    msr elr_el3, x0
    mov x0, #0x3c9
    msr spsr_el3, x0
    isb
    eret

enter_from_el2:
    mov x1, #(1 << 31)
    msr hcr_el2, x1

    mrs x1, cptr_el2
    bic x1, x1, #(1 << 10)
    mrs x2, id_aa64pfr0_el1
    ubfx x3, x2, #32, #4
    cbz x3, no_el2_sve
    orr x1, x1, #(3 << 16)
no_el2_sve:
    msr cptr_el2, x1
    isb

    cbz x3, done_el2_sve
    mov x2, #0xf
    msr zcr_el2, x2
done_el2_sve:
    adr x0, setup_el1
    msr elr_el2, x0
    mov x0, #0x3c5
    msr spsr_el2, x0
    isb
    eret

setup_el1:
    mrs x1, sctlr_el1
    bic x1, x1, #(1 << 1)
    bic x1, x1, #(3 << 3)
    msr sctlr_el1, x1

    mrs x1, cpacr_el1
    orr x1, x1, #(3 << 20)
    mrs x2, id_aa64pfr0_el1
    ubfx x3, x2, #32, #4
    cbz x3, no_el1_sve
    orr x1, x1, #(3 << 16)
no_el1_sve:
    msr cpacr_el1, x1
    isb

    cbz x3, done_el1_sve
    mov x2, #0xf
    msr zcr_el1, x2
done_el1_sve:

    bl setup_el1_mmu
    b setup_runtime

setup_el1_mmu:
    ldr x0, =__translation_table
    mov x1, xzr
    mov x2, #512
1:
    str x1, [x0], #8
    subs x2, x2, #1
    b.ne 1b

    ldr x0, =__translation_table

    /* L1[0]: 0x00000000-0x3fffffff, Device-nGnRnE for MMIO. */
    mov x1, #(1 << 10)
    orr x1, x1, #1
    str x1, [x0]

    /* L1[1..8]: eight contiguous 1 GiB inner-shareable Normal WB blocks. */
    mov x1, #0x40000000
    orr x1, x1, #(1 << 10)
    orr x1, x1, #(3 << 8)
    orr x1, x1, #(1 << 2)
    orr x1, x1, #1
    add x0, x0, #8
    mov x2, #8
    mov x3, #0x40000000
2:
    str x1, [x0], #8
    add x1, x1, x3
    subs x2, x2, #1
    b.ne 2b
    dsb sy

    /* Attr0: Device-nGnRnE, Attr1: Normal WB, read/write allocate. */
    mov x1, #0xff00
    msr mair_el1, x1
    ldr x1, =__translation_table
    msr ttbr0_el1, x1

    /* 39-bit VA, 4 KiB granule, inner-shareable WB table walks. */
    mov x1, #25
    orr x1, x1, #(1 << 8)
    orr x1, x1, #(1 << 10)
    orr x1, x1, #(3 << 12)
    mov x2, #25
    orr x1, x1, x2, lsl #16
    orr x1, x1, #(1 << 23)
    mrs x2, id_aa64mmfr0_el1
    and x2, x2, #0xf
    orr x1, x1, x2, lsl #32
    msr tcr_el1, x1
    isb

    tlbi vmalle1
    dsb sy
    isb

    mrs x1, sctlr_el1
    bic x1, x1, #(1 << 1)
    bic x1, x1, #(3 << 3)
    orr x1, x1, #(1 << 0)
    orr x1, x1, #(1 << 2)
    orr x1, x1, #(1 << 12)
    msr sctlr_el1, x1
    isb
    ret

setup_runtime:
    isb
    ldr x0, =__stack_top
    mov sp, x0

    ldr x0, =__bss_start
    ldr x1, =__bss_end
clear_bss:
    cmp x0, x1
    b.hs bss_done
    stp xzr, xzr, [x0], #16
    b clear_bss
bss_done:
    bl __libc_init_array
    mov x0, xzr
    mov x1, xzr
    bl main
    mov x19, x0
    bl __libc_fini_array
    mov x0, x19
    bl _exit

halt:
    wfe
    b halt

.global _init
_init:
    ret

.global _fini
_fini:
    ret

.section .bss.page_tables, "aw", %nobits
.balign 4096
.global __translation_table
__translation_table:
    .skip 4096
