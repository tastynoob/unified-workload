#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef UART_BASE
#define UART_BASE 0x13000000UL
#endif

extern char __heap_start[];
extern char __heap_end[];

static char *heap_end = __heap_start;
void *__dso_handle = &__dso_handle;

static void uart_putc(char c)
{
    volatile uint32_t *const uart_dr = (volatile uint32_t *)UART_BASE;

    if (c == '\n') {
        *uart_dr = '\r';
    }
    *uart_dr = (uint8_t)c;
}

ssize_t _write(int fd, const void *buffer, size_t length)
{
    const char *bytes = buffer;

    if (fd != 1 && fd != 2) {
        errno = EBADF;
        return -1;
    }
    for (size_t i = 0; i < length; i++) {
        uart_putc(bytes[i]);
    }
    return (ssize_t)length;
}

void *_sbrk(ptrdiff_t increment)
{
    char *previous = heap_end;
    uintptr_t next = (uintptr_t)heap_end + (uintptr_t)increment;

    next = (next + 15U) & ~(uintptr_t)15U;
    if (increment < 0 || next > (uintptr_t)__heap_end) {
        errno = ENOMEM;
        return (void *)-1;
    }
    heap_end = (char *)next;
    return previous;
}

int _close(int fd)
{
    (void)fd;
    errno = EBADF;
    return -1;
}

int _fstat(int fd, struct stat *st)
{
    if (fd != 1 && fd != 2) {
        errno = EBADF;
        return -1;
    }
    st->st_mode = S_IFCHR;
    return 0;
}

int _isatty(int fd)
{
    return fd == 1 || fd == 2;
}

off_t _lseek(int fd, off_t offset, int whence)
{
    (void)fd;
    (void)offset;
    (void)whence;
    errno = ESPIPE;
    return (off_t)-1;
}

ssize_t _read(int fd, void *buffer, size_t length)
{
    (void)fd;
    (void)buffer;
    (void)length;
    errno = ENOSYS;
    return -1;
}

int _gettimeofday(struct timeval *tv, void *timezone)
{
    (void)tv;
    (void)timezone;
    errno = ENOSYS;
    return -1;
}

clock_t _times(struct tms *buffer)
{
    (void)buffer;
    errno = ENOSYS;
    return (clock_t)-1;
}

int _getpid(void)
{
    return 1;
}

int _kill(int pid, int signal)
{
    (void)pid;
    (void)signal;
    errno = EINVAL;
    return -1;
}

int _link(const char *old_path, const char *new_path)
{
    (void)old_path;
    (void)new_path;
    errno = ENOSYS;
    return -1;
}

int chdir(const char *path)
{
    (void)path;
    return 0;
}

int ftruncate(int fd, off_t length)
{
    (void)fd;
    if (length < 0) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

long sysconf(int name)
{
    if (name == _SC_PAGESIZE) {
        return getpagesize();
    }
    return 1;
}

char *getcwd(char *buffer, size_t size)
{
    if (buffer == NULL || size < 2) {
        errno = ERANGE;
        return NULL;
    }
    memcpy(buffer, "/", 2);
    return buffer;
}

int getpagesize(void)
{
    return 4096;
}

__attribute__((noreturn)) void _exit(int status)
{
    (void)status;
    for (;;) {
        __asm__ volatile("wfe");
    }
}
