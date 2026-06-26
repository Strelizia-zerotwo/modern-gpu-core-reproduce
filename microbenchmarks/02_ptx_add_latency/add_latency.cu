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

__global__ void add_latency_kernel(unsigned long long *out, unsigned int *sink) {
    unsigned int x = threadIdx.x + 1;

    unsigned long long start = clock64();

        asm volatile("add.u32 %0, %0, 1;" : "+r"(x));
        asm volatile("add.u32 %0, %0, 1;" : "+r"(x));

    unsigned long long end = clock64();

    out[0] = end - start;
    sink[0] = x;
}

int main() {
    unsigned long long *d_out = nullptr;
    unsigned long long h_out = 0;

    unsigned int *d_sink = nullptr;
    unsigned int h_sink = 0;

    CHECK_CUDA(cudaMalloc(&d_out, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_sink, sizeof(unsigned int)));

    add_latency_kernel<<<1, 1>>>(d_out, d_sink);

    CHECK_CUDA(cudaGetLastError());
    CHECK_CUDA(cudaDeviceSynchronize());

    CHECK_CUDA(cudaMemcpy(&h_out, d_out,
                          sizeof(unsigned long long),
                          cudaMemcpyDeviceToHost));

    CHECK_CUDA(cudaMemcpy(&h_sink, d_sink,
                          sizeof(unsigned int),
                          cudaMemcpyDeviceToHost));

    printf("elapsed cycles = %llu\n", h_out);
    printf("sink = %u\n", h_sink);

    CHECK_CUDA(cudaFree(d_out));
    CHECK_CUDA(cudaFree(d_sink));

    return 0;
}
