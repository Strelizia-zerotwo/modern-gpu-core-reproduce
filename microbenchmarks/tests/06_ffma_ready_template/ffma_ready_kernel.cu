#include <cuda_runtime.h>

extern "C" __global__
void ffma_reg_kernel(unsigned long long *cycles, float *sink, const float *in) {
    unsigned int tid;

    asm volatile(
        "mov.u32 %0, %%tid.x;"
        : "=r"(tid)
    );

    float a = (float)(tid + 2);  // thread 0: 2.0
    float b = (float)(tid + 3);  // thread 0: 3.0
    float c = (float)(tid + 5);  // thread 0: 5.0
    float d = (float)(tid + 7);
    float e = (float)(tid + 11);

    asm volatile("" :: "f"(a), "f"(b), "f"(c), "f"(d), "f"(e) : "memory");

    unsigned long long start = clock64();

    float y;

    asm volatile(
        "fma.rn.f32 %0, %1, %2, %3;"
        : "=f"(y)
        : "f"(a), "f"(b), "f"(c)
    );

    unsigned long long end = clock64();

    asm volatile("" :: "f"(d), "f"(e), "f"(y) : "memory");

    cycles[0] = end - start;
    sink[0] = y;
}
