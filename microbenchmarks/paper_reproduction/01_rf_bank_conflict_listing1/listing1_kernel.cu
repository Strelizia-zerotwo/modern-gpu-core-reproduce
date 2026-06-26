#include <cuda_runtime.h>

extern "C" __global__
void listing1_kernel(unsigned long long *cycles, float *sink) {
    unsigned int tid;
    asm volatile("mov.u32 %0, %%tid.x;" : "=r"(tid));

    float v0  = (float)(tid + 0);
    float v1  = (float)(tid + 1);
    float v2  = (float)(tid + 2);
    float v3  = (float)(tid + 3);
    float v4  = (float)(tid + 4);
    float v5  = (float)(tid + 5);
    float v6  = (float)(tid + 6);
    float v7  = (float)(tid + 7);
    float v8  = (float)(tid + 8);
    float v9  = (float)(tid + 9);
    float v10 = (float)(tid + 10);
    float v11 = (float)(tid + 11);
    float v12 = (float)(tid + 12);
    float v13 = (float)(tid + 13);
    float v14 = (float)(tid + 14);
    float v15 = (float)(tid + 15);
    float v16 = (float)(tid + 16);
    float v17 = (float)(tid + 17);
    float v18 = (float)(tid + 18);
    float v19 = (float)(tid + 19);
    float v20 = (float)(tid + 20);
    float v21 = (float)(tid + 21);
    float v22 = (float)(tid + 22);
    float v23 = (float)(tid + 23);

    asm volatile("" ::
        "f"(v0),  "f"(v1),  "f"(v2),  "f"(v3),
        "f"(v4),  "f"(v5),  "f"(v6),  "f"(v7),
        "f"(v8),  "f"(v9),  "f"(v10), "f"(v11),
        "f"(v12), "f"(v13), "f"(v14), "f"(v15),
        "f"(v16), "f"(v17), "f"(v18), "f"(v19),
        "f"(v20), "f"(v21), "f"(v22), "f"(v23)
        : "memory"
    );

    unsigned long long start = clock64();

    float y0;
    float y1;

    asm volatile(
        "fma.rn.f32 %0, %2, %3, %4;\n\t"
        "fma.rn.f32 %1, %5, %6, %7;\n\t"
        : "=f"(y0), "=f"(y1)
        : "f"(v10), "f"(v12), "f"(v14),
          "f"(v16), "f"(v18), "f"(v20)
    );

    unsigned long long end = clock64();

    float keep;
    asm volatile(
        "add.rn.f32 %0, %1, %2;\n\t"
        "add.rn.f32 %0, %0, %3;\n\t"
        "add.rn.f32 %0, %0, %4;\n\t"
        "add.rn.f32 %0, %0, %5;\n\t"
        "add.rn.f32 %0, %0, %6;\n\t"
        "add.rn.f32 %0, %0, %7;\n\t"
        "add.rn.f32 %0, %0, %8;\n\t"
        "add.rn.f32 %0, %0, %9;\n\t"
        "add.rn.f32 %0, %0, %10;\n\t"
        "add.rn.f32 %0, %0, %11;\n\t"
        "add.rn.f32 %0, %0, %12;\n\t"
        "add.rn.f32 %0, %0, %13;\n\t"
        "add.rn.f32 %0, %0, %14;\n\t"
        "add.rn.f32 %0, %0, %15;\n\t"
        "add.rn.f32 %0, %0, %16;\n\t"
        "add.rn.f32 %0, %0, %17;\n\t"
        "add.rn.f32 %0, %0, %18;\n\t"
        "add.rn.f32 %0, %0, %19;\n\t"
        "add.rn.f32 %0, %0, %20;\n\t"
        "add.rn.f32 %0, %0, %21;\n\t"
        "add.rn.f32 %0, %0, %22;\n\t"
        "add.rn.f32 %0, %0, %23;\n\t"
        "add.rn.f32 %0, %0, %24;\n\t"
        : "=f"(keep)
        : "f"(v0),  "f"(v1),  "f"(v2),  "f"(v3),
          "f"(v4),  "f"(v5),  "f"(v6),  "f"(v7),
          "f"(v8),  "f"(v9),  "f"(v10), "f"(v11),
          "f"(v12), "f"(v13), "f"(v14), "f"(v15),
          "f"(v16), "f"(v17), "f"(v18), "f"(v19),
          "f"(v20), "f"(v21), "f"(v22), "f"(v23)
    );

    cycles[0] = end - start;
    sink[0] = y0 + y1 + keep * 1.0e-30f;
}
