#include "simtrap.h"

#include <stdlib.h>

int __real_main(int argc, char **argv);

static int profile_stopped;

static void profile_stop(void)
{
    if (!profile_stopped) {
        profile_stopped = 1;
        SIMTRAP_PROFILE_STOP();
    }
}

int __wrap_main(int argc, char **argv)
{
    int status;

    (void)atexit(profile_stop);
    SIMTRAP_PROFILE_START();
    status = __real_main(argc, argv);
    profile_stop();
    return status;
}
