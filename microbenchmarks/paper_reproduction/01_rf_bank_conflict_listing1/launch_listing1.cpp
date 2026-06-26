#include <cstdio>
#include <cuda.h>

#define CHECK_DRV(call) do {                                      \
    CUresult err = call;                                          \
    if (err != CUDA_SUCCESS) {                                    \
        const char *name = nullptr;                               \
        const char *msg = nullptr;                                \
        cuGetErrorName(err, &name);                               \
        cuGetErrorString(err, &msg);                              \
        printf("CUDA driver error at %s:%d: %s, %s\n",            \
               __FILE__, __LINE__,                               \
               name ? name : "unknown",                          \
               msg ? msg : "unknown");                           \
        return 1;                                                 \
    }                                                            \
} while (0)

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("usage: %s kernel.cubin\n", argv[0]);
        return 1;
    }

    const char *cubin_path = argv[1];

    CHECK_DRV(cuInit(0));

    CUdevice dev;
    CHECK_DRV(cuDeviceGet(&dev, 0));

    CUcontext ctx;
    CHECK_DRV(cuCtxCreate(&ctx, 0, dev));

    CUmodule mod;
    CHECK_DRV(cuModuleLoad(&mod, cubin_path));

    CUfunction func;
    CHECK_DRV(cuModuleGetFunction(&func, mod, "listing1_kernel"));

    CUdeviceptr d_cycles;
    CUdeviceptr d_sink;

    CHECK_DRV(cuMemAlloc(&d_cycles, sizeof(unsigned long long)));
    CHECK_DRV(cuMemAlloc(&d_sink, sizeof(float)));

    void *args[] = { &d_cycles, &d_sink };

    unsigned long long min_cycles = ~0ULL;
    unsigned long long sum_cycles = 0;

    for (int i = 0; i < 50; i++) {
        CHECK_DRV(cuMemsetD32(d_cycles, 0, 2));
        CHECK_DRV(cuMemsetD32(d_sink, 0, 1));

        CHECK_DRV(cuLaunchKernel(
            func,
            1, 1, 1,
            1, 1, 1,
            0,
            0,
            args,
            nullptr
        ));

        CHECK_DRV(cuCtxSynchronize());

        unsigned long long h_cycles = 0;
        float h_sink = 0.0f;

        CHECK_DRV(cuMemcpyDtoH(&h_cycles, d_cycles, sizeof(unsigned long long)));
        CHECK_DRV(cuMemcpyDtoH(&h_sink, d_sink, sizeof(float)));

        if (h_cycles < min_cycles) min_cycles = h_cycles;
        sum_cycles += h_cycles;

        printf("run %02d: cycles = %llu, sink = %.6f\n", i, h_cycles, h_sink);
    }

    printf("min cycles = %llu\n", min_cycles);
    printf("avg cycles = %.2f\n", (double)sum_cycles / 50.0);

    CHECK_DRV(cuMemFree(d_cycles));
    CHECK_DRV(cuMemFree(d_sink));
    CHECK_DRV(cuModuleUnload(mod));
    CHECK_DRV(cuCtxDestroy(ctx));

    return 0;
}
