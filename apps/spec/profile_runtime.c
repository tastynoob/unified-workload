#include "simtrap.h"

#include <stdlib.h>

int __real_main(int argc, char **argv);
extern const int spec_argc;
extern char *spec_argv[];

static int spec_profile_stopped;

static void spec_profile_stop(void)
{
    if (!spec_profile_stopped) {
        spec_profile_stopped = 1;
        SIMTRAP_PROFILE_STOP();
    }
}

int __wrap_main(int argc, char **argv)
{
    int status;

    (void)argc;
    (void)argv;
    SIMTRAP_PROFILE_START();
    atexit(spec_profile_stop);
    status = __real_main(spec_argc, spec_argv);
    spec_profile_stop();
    return status;
}
