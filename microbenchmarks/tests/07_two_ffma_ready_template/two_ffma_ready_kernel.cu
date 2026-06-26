#include <cuda_runtime.h>

extern "C" __global__
void ffma_reg_kernel(unsigned long long *cycles, float *sink, const float *in) {
    unsigned int tid;

    asm volatile(
        "mov.u32 %0, %%tid.x;"
        : "=r"(tid)
    );

    float a0 = (float)(tid + 2);   // thread 0: 2
    float b0 = (float)(tid + 3);   // thread 0: 3
    float c0 = (float)(tid + 5);   // thread 0: 5

    float a1 = (float)(tid + 7);   // thread 0: 7
    float b1 = (float)(tid + 11);  // thread 0: 11
    float c1 = (float)(tid + 13);  // thread 0: 13

    asm volatile("" :: "f"(a0), "f"(b0), "f"(c0), "f"(a1), "f"(b1), "f"(c1) : "memory");

    unsigned long long start = clock64();

    float y0;
    float y1;

    asm volatile(
        "fma.rn.f32 %0, %2, %3, %4;\n\t"
        "fma.rn.f32 %1, %5, %6, %7;\n\t"
        : "=f"(y0), "=f"(y1)
        : "f"(a0), "f"(b0), "f"(c0),
          "f"(a1), "f"(b1), "f"(c1)
    );

    unsigned long long end = clock64();

    cycles[0] = end - start;
    sink[0] = y0 + y1;
}
