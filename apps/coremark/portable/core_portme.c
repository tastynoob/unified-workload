#include "coremark.h"

#include <simtrap.h>

#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#define NSECS_PER_SEC 1000000000ULL
#define TIMER_RES_DIVIDER 1000000ULL
#define EE_TICKS_PER_SEC (NSECS_PER_SEC / TIMER_RES_DIVIDER)

static struct timespec start_time_val;
static struct timespec stop_time_val;

void *
portable_malloc(ee_size_t size)
{
    return malloc(size);
}

void
portable_free(void *p)
{
    free(p);
}

static CORE_TICKS
elapsed_ticks(const struct timespec *start, const struct timespec *stop)
{
    uint64_t start_ns =
        (uint64_t)start->tv_sec * NSECS_PER_SEC + (uint64_t)start->tv_nsec;
    uint64_t stop_ns =
        (uint64_t)stop->tv_sec * NSECS_PER_SEC + (uint64_t)stop->tv_nsec;

    return (CORE_TICKS)((stop_ns - start_ns) / TIMER_RES_DIVIDER);
}

void
start_time(void)
{
    clock_gettime(CLOCK_MONOTONIC, &start_time_val);
}

void
stop_time(void)
{
    clock_gettime(CLOCK_MONOTONIC, &stop_time_val);
}

CORE_TICKS
get_time(void)
{
    return elapsed_ticks(&start_time_val, &stop_time_val);
}

secs_ret
time_in_secs(CORE_TICKS ticks)
{
    return ((secs_ret)ticks) / (secs_ret)EE_TICKS_PER_SEC;
}

ee_u32 default_num_contexts = 1;

void
portable_init(core_portable *p, int *argc, char *argv[])
{
    (void)argc;
    (void)argv;

    if (sizeof(ee_ptr_int) != sizeof(ee_u8 *))
    {
        ee_printf("ERROR! ee_ptr_int must hold a pointer.\n");
    }
    if (sizeof(ee_u32) != 4)
    {
        ee_printf("ERROR! ee_u32 must be a 32-bit unsigned type.\n");
    }

    p->portable_id = 1;
    SIMTRAP_PROFILE_START();
}

void
portable_fini(core_portable *p)
{
    SIMTRAP_PROFILE_STOP();
    SIMTRAP_SIGNAL(SIMTRAP_GOOD_TRAP);
    p->portable_id = 0;
}
