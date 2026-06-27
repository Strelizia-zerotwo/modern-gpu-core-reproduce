#include <cuda_runtime.h>

extern "C" __global__
void lowreg_kernel(unsigned long long *cycles, float *sink, float *guard) {
    unsigned int tid;
    asm volatile("mov.u32 %0, %%tid.x;" : "=r"(tid));

    unsigned int u10 = tid + 10;
    unsigned int u12 = tid + 12;
    unsigned int u14 = tid + 14;
    unsigned int u16 = tid + 16;
    unsigned int u18 = tid + 18;
    unsigned int u19 = tid + 19;
    unsigned int u20 = tid + 20;
    unsigned int u21 = tid + 21;

    float v10, v12, v14, v16, v18, v19, v20, v21;

    asm volatile(
        "cvt.rn.f32.u32 %0, %8;\n\t"
        "cvt.rn.f32.u32 %1, %9;\n\t"
        "cvt.rn.f32.u32 %2, %10;\n\t"
        "cvt.rn.f32.u32 %3, %11;\n\t"
        "cvt.rn.f32.u32 %4, %12;\n\t"
        "cvt.rn.f32.u32 %5, %13;\n\t"
        "cvt.rn.f32.u32 %6, %14;\n\t"
        "cvt.rn.f32.u32 %7, %15;\n\t"
        : "=f"(v10), "=f"(v12), "=f"(v14), "=f"(v16),
          "=f"(v18), "=f"(v19), "=f"(v20), "=f"(v21)
        : "r"(u10), "r"(u12), "r"(u14), "r"(u16),
          "r"(u18), "r"(u19), "r"(u20), "r"(u21)
    );

    // Wait padding before the clock window.
    // This is outside measurement. It only ensures v10..v21 are ready.
    unsigned int pre_dummy = tid;
    asm volatile(
        "add.u32 %0, %0, 1;\n\t"
        "add.u32 %0, %0, 2;\n\t"
        "add.u32 %0, %0, 3;\n\t"
        "add.u32 %0, %0, 4;\n\t"
        "add.u32 %0, %0, 5;\n\t"
        "add.u32 %0, %0, 6;\n\t"
        "add.u32 %0, %0, 7;\n\t"
        "add.u32 %0, %0, 8;\n\t"
        : "+r"(pre_dummy)
    );

    unsigned long long start = clock64();

    float y0;
    float y1;
    unsigned int dummy = tid;

    asm volatile(
        "add.u32 %0, %0, 1;\n\t"
        "fma.rn.f32 %1, %3, %4, %5;\n\t"
        "fma.rn.f32 %2, %6, %7, %8;\n\t"
        "add.u32 %0, %0, 2;\n\t"
        : "+r"(dummy), "=f"(y0), "=f"(y1)
        : "f"(v10), "f"(v12), "f"(v14),
          "f"(v16), "f"(v18), "f"(v20)
    );

    unsigned long long end = clock64();

    float keep;
    asm volatile(
        "add.rn.f32 %0, %1, %2;\n\t"
        : "=f"(keep)
        : "f"(v19), "f"(v21)
    );

    cycles[0] = end - start;
    sink[0] = y0 + y1;
    guard[0] = (float)(dummy + pre_dummy) + keep * 1.0e-30f;
}
