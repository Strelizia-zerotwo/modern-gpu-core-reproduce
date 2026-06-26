# 03 SASS Patch Test

This experiment verifies that we can manually patch SASS machine code inside a Blackwell sm_120 cubin.

Original instruction:

```sass
IADD3 R5, PT, PT, R5, 0x1, RZ
Patched instruction:

NOP

Original output:

sink = 1

Patched output:

sink = 0

This confirms that the modified cubin is actually executed by the GPU.
```bash
