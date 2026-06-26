#include <cuda_runtime.h>

extern "C" __global__
void ffma_reg_kernel(unsigned long long *cycles, float *sink, const float *in) {
    float a = in[0];
    float b = in[1];
    float c = in[2];

    float y;

    asm volatile("" ::: "memory");

    unsigned long long start = clock64();

    asm volatile(
        "fma.rn.f32 %0, %1, %2, %3;"
        : "=f"(y)
        : "f"(a), "f"(b), "f"(c)
    );

    unsigned long long end = clock64();

    cycles[0] = end - start;
    sink[0] = y;
}
