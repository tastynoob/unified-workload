#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

struct spec_embedded_file {
    const char *path;
    size_t offset;
    size_t size;
};

extern const unsigned char _binary_spec_inputs_bin_start[];
extern const struct spec_embedded_file spec_embedded_files[];
extern const size_t spec_embedded_file_count;
extern const int spec_argc;
extern char *spec_argv[];
extern const char *spec_stdin_path;

int __real_main(int argc, char **argv);
ssize_t __real__write(int fd, const void *buffer, size_t length);
int __real__fstat(int fd, struct stat *st);
off_t __real__lseek(int fd, off_t offset, int whence);
int __real__close(int fd);

enum handle_kind {
    HANDLE_FREE,
    HANDLE_INPUT,
    HANDLE_SINK,
};

struct file_handle {
    enum handle_kind kind;
    const struct spec_embedded_file *file;
    size_t position;
    int flags;
};

#define SPEC_MAX_FDS 32

static struct file_handle handles[SPEC_MAX_FDS];

static const char *normalize_path(const char *path)
{
    while (path[0] == '.' && path[1] == '/') {
        path += 2;
    }
    return path;
}

static const struct spec_embedded_file *find_input(const char *path)
{
    path = normalize_path(path);
    for (size_t i = 0; i < spec_embedded_file_count; i++) {
        if (strcmp(path, spec_embedded_files[i].path) == 0) {
            return &spec_embedded_files[i];
        }
    }
    return (const struct spec_embedded_file *)0;
}

static int allocate_fd(void)
{
    for (int fd = 3; fd < SPEC_MAX_FDS; fd++) {
        if (handles[fd].kind == HANDLE_FREE) {
            return fd;
        }
    }
    errno = EMFILE;
    return -1;
}

static void reset_handles(void)
{
    memset(handles, 0, sizeof(handles));
    if (spec_stdin_path != (const char *)0) {
        handles[0].kind = HANDLE_INPUT;
        handles[0].file = find_input(spec_stdin_path);
        handles[0].flags = O_RDONLY;
    }
}

int __wrap_main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    reset_handles();
    return __real_main(spec_argc, spec_argv);
}

int __wrap__open(const char *path, int flags, ...)
{
    const struct spec_embedded_file *file = find_input(path);
    int access_mode = flags & O_ACCMODE;
    int fd = allocate_fd();

    if (fd < 0) {
        return -1;
    }
    if (access_mode != O_WRONLY && file != (const void *)0) {
        handles[fd].kind = HANDLE_INPUT;
        handles[fd].file = file;
    } else if (access_mode != O_RDONLY || (flags & O_CREAT) != 0) {
        handles[fd].kind = HANDLE_SINK;
    } else {
        errno = ENOENT;
        return -1;
    }
    handles[fd].flags = flags;
    return fd;
}

ssize_t __wrap__read(int fd, void *buffer, size_t length)
{
    struct file_handle *handle;
    size_t remaining;

    if (fd < 0 || fd >= SPEC_MAX_FDS) {
        errno = EBADF;
        return -1;
    }
    handle = &handles[fd];
    if (handle->kind == HANDLE_FREE && fd == 0) {
        return 0;
    }
    if (handle->kind != HANDLE_INPUT ||
        (handle->flags & O_ACCMODE) == O_WRONLY) {
        errno = EBADF;
        return -1;
    }
    if (handle->position >= handle->file->size) {
        return 0;
    }
    remaining = handle->file->size - handle->position;
    if (length > remaining) {
        length = remaining;
    }
    memcpy(buffer,
           _binary_spec_inputs_bin_start + handle->file->offset +
               handle->position,
           length);
    handle->position += length;
    return (ssize_t)length;
}

ssize_t __wrap__write(int fd, const void *buffer, size_t length)
{
    struct file_handle *handle;

    if (fd == 1 || fd == 2) {
        return __real__write(fd, buffer, length);
    }
    if (fd < 0 || fd >= SPEC_MAX_FDS) {
        errno = EBADF;
        return -1;
    }
    handle = &handles[fd];
    if (handle->kind == HANDLE_FREE ||
        (handle->flags & O_ACCMODE) == O_RDONLY) {
        errno = EBADF;
        return -1;
    }
    handle->position += length;
    return (ssize_t)length;
}

off_t __wrap__lseek(int fd, off_t offset, int whence)
{
    struct file_handle *handle;
    int64_t base;
    int64_t position;

    if (fd < 0 || fd >= SPEC_MAX_FDS || handles[fd].kind == HANDLE_FREE) {
        return __real__lseek(fd, offset, whence);
    }
    handle = &handles[fd];
    if (whence == SEEK_SET) {
        base = 0;
    } else if (whence == SEEK_CUR) {
        base = (int64_t)handle->position;
    } else if (whence == SEEK_END) {
        base = handle->kind == HANDLE_INPUT ? (int64_t)handle->file->size :
                                              (int64_t)handle->position;
    } else {
        errno = EINVAL;
        return (off_t)-1;
    }
    position = base + (int64_t)offset;
    if (position < 0) {
        errno = EINVAL;
        return (off_t)-1;
    }
    handle->position = (size_t)position;
    return (off_t)position;
}

int __wrap__fstat(int fd, struct stat *st)
{
    if (fd >= 0 && fd < SPEC_MAX_FDS && handles[fd].kind != HANDLE_FREE) {
        memset(st, 0, sizeof(*st));
        st->st_mode = S_IFREG;
        if (handles[fd].kind == HANDLE_INPUT) {
            st->st_size = (off_t)handles[fd].file->size;
        }
        return 0;
    }
    if (fd == 0) {
        memset(st, 0, sizeof(*st));
        st->st_mode = S_IFCHR;
        return 0;
    }
    return __real__fstat(fd, st);
}

int __wrap__stat(const char *path, struct stat *st)
{
    const struct spec_embedded_file *file;

    memset(st, 0, sizeof(*st));
    path = normalize_path(path);
    if (strcmp(path, ".") == 0 || strcmp(path, "/") == 0) {
        st->st_mode = S_IFDIR;
        return 0;
    }
    file = find_input(path);
    if (file == (const void *)0) {
        errno = ENOENT;
        return -1;
    }
    st->st_mode = S_IFREG;
    st->st_size = (off_t)file->size;
    return 0;
}

int __wrap__unlink(const char *path)
{
    (void)path;
    return 0;
}

int __wrap__close(int fd)
{
    if (fd >= 3 && fd < SPEC_MAX_FDS && handles[fd].kind != HANDLE_FREE) {
        memset(&handles[fd], 0, sizeof(handles[fd]));
        return 0;
    }
    return __real__close(fd);
}
