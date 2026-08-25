#include "coremark.h"

#if COREMARK_CHECKPOINT
#include <simtrap.h>
#endif

#define PERFORMANCE_RUN 1

volatile ee_s32 seed1_volatile = 0;
volatile ee_s32 seed2_volatile = 0;
volatile ee_s32 seed3_volatile = 0x66;
volatile ee_s32 seed4_volatile = ITERATIONS;
volatile ee_s32 seed5_volatile = 0;

void start_time(void)
{
#if COREMARK_CHECKPOINT
    SIMTRAP_PROFILE_START();
#endif
}

void stop_time(void)
{
}

CORE_TICKS get_time(void)
{
    return 1;
}

secs_ret time_in_secs(CORE_TICKS ticks)
{
    (void)ticks;
    return 1;
}

ee_u32 default_num_contexts = 1;

void portable_init(core_portable *p, int *argc, char *argv[])
{
    (void)argc;
    (void)argv;

    p->portable_id = 1;
}

void portable_fini(core_portable *p)
{
    p->portable_id = 0;
#if COREMARK_CHECKPOINT
    SIMTRAP_SIGNAL(SIMTRAP_GOOD_TRAP);
#endif
}
