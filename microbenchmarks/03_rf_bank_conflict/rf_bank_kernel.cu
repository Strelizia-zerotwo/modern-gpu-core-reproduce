#include <cuda_runtime.h>

extern "C" __global__
void rf_bank_kernel(unsigned long long *out, float *sink) {
    float a = 1.0f + threadIdx.x;
    float b = 2.0f;
    float c = 3.0f;
    float d = 4.0f;

    unsigned long long start = clock64();

    float x = fmaf(a, b, c);
    float y = fmaf(x, c, d);

    unsigned long long end = clock64();

    out[0] = end - start;
    sink[0] = y;
}
