#include <stdint.h>
#include <stdio.h>

#include <simtrap.h>

#define GEMM_N 64

static int32_t a[GEMM_N][GEMM_N];
static int32_t b[GEMM_N][GEMM_N];
static int64_t c[GEMM_N][GEMM_N];

static volatile int64_t gemm_sink;

static void __attribute__((noinline)) init_matrices(void)
{
    for (int i = 0; i < GEMM_N; i++) {
        for (int j = 0; j < GEMM_N; j++) {
            a[i][j] = (int32_t)(((i * 17) + (j * 3) + 1) & 0x7f);
            b[i][j] = (int32_t)(((i * 5) - (j * 11) + 7) & 0x7f);
            c[i][j] = 0;
        }
    }
}

static void __attribute__((noinline)) gemm_kernel(void)
{
    for (int i = 0; i < GEMM_N; i++) {
        for (int j = 0; j < GEMM_N; j++) {
            int64_t sum = 0;

            for (int k = 0; k < GEMM_N; k++) {
                sum += (int64_t)a[i][k] * b[k][j];
            }
            c[i][j] = sum;
        }
    }
}

static int64_t __attribute__((noinline)) checksum_matrix(void)
{
    int64_t checksum = 0;

    for (int i = 0; i < GEMM_N; i++) {
        for (int j = 0; j < GEMM_N; j++) {
            checksum += c[i][j] ^ (int64_t)(i * 131 + j);
        }
    }
    return checksum;
}

int main(void)
{
    SIMTRAP_PROFILE_START();
    init_matrices();
    gemm_kernel();
    gemm_sink = checksum_matrix();
    printf("gemm n=%d checksum=%lld\n", GEMM_N, (long long)gemm_sink);
    SIMTRAP_PROFILE_STOP();

    puts("hanging");
    while (1) {
    }
}
