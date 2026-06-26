#include <cuda_runtime.h>

extern "C" __global__
void patch_test_kernel(unsigned int *sink) {
    unsigned int x = threadIdx.x;

    asm volatile("add.u32 %0, %0, 1;" : "+r"(x));

    sink[0] = x;
}
