#include <cuda_runtime.h>

extern "C" __global__
void ffma_patch_kernel(unsigned long long *cycles, float *sink) {
    float a = 1.0f + (float)threadIdx.x;
    float b = 2.0f;
    float y = 7.0f;

    unsigned long long start = clock64();

    asm volatile(
        "fma.rn.f32 %0, %1, %2, %0;"
        : "+f"(y)
        : "f"(a), "f"(b)
    );

    unsigned long long end = clock64();

    cycles[0] = end - start;
    sink[0] = y;
}
