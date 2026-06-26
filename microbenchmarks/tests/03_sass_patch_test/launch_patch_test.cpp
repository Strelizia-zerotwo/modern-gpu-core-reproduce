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
    CHECK_DRV(cuModuleGetFunction(&func, mod, "patch_test_kernel"));

    CUdeviceptr d_sink;
    CHECK_DRV(cuMemAlloc(&d_sink, sizeof(unsigned int)));
    CHECK_DRV(cuMemsetD32(d_sink, 0, 1));

    void *args[] = { &d_sink };

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

    unsigned int h_sink = 999;
    CHECK_DRV(cuMemcpyDtoH(&h_sink, d_sink, sizeof(unsigned int)));

    printf("sink = %u\n", h_sink);

    CHECK_DRV(cuMemFree(d_sink));
    CHECK_DRV(cuModuleUnload(mod));
    CHECK_DRV(cuCtxDestroy(ctx));

    return 0;
}
