#ifndef UNIFIED_WORKLOAD_SIMTRAP_H
#define UNIFIED_WORKLOAD_SIMTRAP_H

#define SIMTRAP_GOOD_TRAP 0x000
#define SIMTRAP_DISABLE_TIME_INTR 0x100
#define SIMTRAP_NOTIFY_PROFILER 0x101
#define SIMTRAP_NOTIFY_WORKLOAD_EXIT 0x102

static inline void simtrap_signal(long signal)
{
    asm volatile(
        "mv a0, %0\n\t"
        ".insn r 0x6B, 0, 0, x0, x0, x0\n\t"
        :
        : "r"(signal)
        : "a0", "memory");
}

#define SIMTRAP_SIGNAL(signal) simtrap_signal(signal)
#define SIMTRAP_PROFILE_START() simtrap_signal(SIMTRAP_NOTIFY_PROFILER)
#define SIMTRAP_PROFILE_STOP() simtrap_signal(SIMTRAP_NOTIFY_WORKLOAD_EXIT)

#endif
