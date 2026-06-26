#include <cstdio>
#include <cuda_runtime.h>

#define CHECK_CUDA(call) do {                                      \
    cudaError_t err = call;                                        \
    if (err != cudaSuccess) {                                      \
        printf("CUDA error at %s:%d: %s\n",                        \
               __FILE__, __LINE__, cudaGetErrorString(err));       \
        return 1;                                                  \
    }                                                             \
} while (0)

__global__ void clock_kernel(unsigned long long *out) {
    unsigned long long start = clock64();

    asm volatile("add.u32 %0, %0, 1;" : "+r"(x));

    unsigned long long end = clock64();

    out[0] = end - start;
}

int main() {
    unsigned long long *d_out = nullptr;
    unsigned long long h_out = 0;

    CHECK_CUDA(cudaMalloc(&d_out, sizeof(unsigned long long)));

    clock_kernel<<<1, 1>>>(d_out);

    CHECK_CUDA(cudaGetLastError());
    CHECK_CUDA(cudaDeviceSynchronize());

    CHECK_CUDA(cudaMemcpy(&h_out, d_out,
                          sizeof(unsigned long long),
                          cudaMemcpyDeviceToHost));

    printf("elapsed cycles = %llu\n", h_out);

    CHECK_CUDA(cudaFree(d_out));

    return 0;
}