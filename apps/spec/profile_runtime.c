#include "simtrap.h"

int __real_main(int argc, char **argv);
extern const int spec_argc;
extern char *spec_argv[];

int __wrap_main(int argc, char **argv)
{
    int status;

    (void)argc;
    (void)argv;
    SIMTRAP_PROFILE_START();
    status = __real_main(spec_argc, spec_argv);
    SIMTRAP_PROFILE_STOP();
    return status;
}
