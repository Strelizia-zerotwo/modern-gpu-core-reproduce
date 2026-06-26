#include <cstdio>
#include <cuda_runtime.h>

__global__ void clock_kernel(unsigned long long *out) {
    unsigned long long start = clock64();

    // 先不放任何手写汇编，只测试 clock64 能不能正常工作
    unsigned long long end = clock64();

    out[0] = end - start;
}

int main() {
    unsigned long long *d_out = nullptr;
    unsigned long long h_out = 0;

    cudaMalloc(&d_out, sizeof(unsigned long long));

    clock_kernel<<<1, 1>>>(d_out);
    cudaDeviceSynchronize();

    cudaMemcpy(&h_out, d_out, sizeof(unsigned long long), cudaMemcpyDeviceToHost);

    printf("elapsed cycles = %llu\n", h_out);

    cudaFree(d_out);
    return 0;
}