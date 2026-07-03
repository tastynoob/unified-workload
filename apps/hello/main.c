#include <stdio.h>

#include <simtrap.h>

int main(void)
{
    SIMTRAP_PROFILE_START();
    puts("hello");
    SIMTRAP_PROFILE_STOP();
    puts("hanging");
    while (1) {
    }
}
