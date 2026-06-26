import struct
from pathlib import Path

infile = Path("patch_test_kernel.cubin")
outfile = Path("patch_iadd_to_nop.cubin")

data = bytearray(infile.read_bytes())

old_inst = 0x0000000105057810
old_ctrl = 0x001fca0007ffe0ff

new_inst = 0x0000000000007918
new_ctrl = 0x000fc00000000000

old_bytes = struct.pack("<QQ", old_inst, old_ctrl)
new_bytes = struct.pack("<QQ", new_inst, new_ctrl)

count = data.count(old_bytes)
print(f"matched instruction count = {count}")

if count != 1:
    raise RuntimeError("Expected exactly one matched IADD3 instruction. Stop to avoid patching wrong bytes.")

offset = data.find(old_bytes)
print(f"patch file offset = 0x{offset:x}")

data[offset:offset + 16] = new_bytes

outfile.write_bytes(data)
print(f"wrote {outfile}")
