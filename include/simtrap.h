#ifndef UNIFIED_WORKLOAD_SIMTRAP_H
#define UNIFIED_WORKLOAD_SIMTRAP_H

#define SIMTRAP_GOOD_TRAP 0x000
#define SIMTRAP_DISABLE_TIME_INTR 0x100
#define SIMTRAP_NOTIFY_PROFILER 0x101
#define SIMTRAP_NOTIFY_WORKLOAD_EXIT 0x102
#define SIMTRAP_INSTRUCTION_CUTPOINT_IMM 0x103

static inline void simtrap_signal(long signal)
{
    (void)signal;
}

#define SIMTRAP_SIGNAL(signal) ((void)(signal))
#define SIMTRAP_PROFILE_START() ((void)0)
#define SIMTRAP_PROFILE_STOP() ((void)0)
#define SIMTRAP_INSTRUCTION_CUTPOINT() ((void)0)

#endif
