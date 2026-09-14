#include "simtrap.h"

#include <stdio.h>
#include <stdlib.h>

int __real_main(int argc, char **argv);
extern const int spec_argc;
extern char *spec_argv[];
extern const char spec_stdin[];
extern const char spec_stdout[];
extern const char spec_stderr[];

static int spec_profile_stopped;

static void spec_profile_stop(void)
{
    if (!spec_profile_stopped) {
        spec_profile_stopped = 1;
        SIMTRAP_PROFILE_STOP();
    }
}

static int redirect_stream(const char *path, const char *mode, FILE *stream)
{
    return path[0] == '\0' || freopen(path, mode, stream) != NULL;
}

int __wrap_main(int argc, char **argv)
{
    int status;

    (void)argc;
    (void)argv;
    if (!redirect_stream(spec_stdin, "r", stdin) ||
        !redirect_stream(spec_stdout, "w", stdout) ||
        !redirect_stream(spec_stderr, "w", stderr)) {
        return 127;
    }
    atexit(spec_profile_stop);
    SIMTRAP_PROFILE_START();
    status = __real_main(spec_argc, spec_argv);
    spec_profile_stop();
    return status;
}
