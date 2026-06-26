import re
import struct
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print("usage: python3 patch_ffma_ready_src_regs.py src2_reg src3_reg output.cubin")
    print("example: python3 patch_ffma_ready_src_regs.py 0 5 ffma_s2_0_s3_5.cubin")
    sys.exit(1)

src2 = int(sys.argv[1])
src3 = int(sys.argv[2])
outfile = Path(sys.argv[3])

infile = Path("ffma_ready_kernel.cubin")
sassfile = Path("ffma_ready_kernel.sass")

sass = sassfile.read_text()
lines = sass.splitlines()

old_inst = None
old_ctrl = None

for i, line in enumerate(lines):
    if "FFMA" in line:
        m_inst = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", line)
        m_ctrl = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", lines[i + 1])
        if m_inst and m_ctrl:
            old_inst = int(m_inst.group(1), 16)
            old_ctrl = int(m_ctrl.group(1), 16)
            print("old FFMA:")
            print(line.strip())
            print(lines[i + 1].strip())
            break

if old_inst is None:
    raise RuntimeError("No FFMA found.")

# Observed sm_120 FFMA form:
# FFMA R9, R0, R3, R5
# src2 = inst bits 32~39
# src3 = ctrl low 8 bits

new_inst = old_inst
new_ctrl = old_ctrl

new_inst &= ~(0xff << 32)
new_inst |= (src2 & 0xff) << 32

new_ctrl &= ~0xff
new_ctrl |= (src3 & 0xff)

print(f"old inst = 0x{old_inst:016x}")
print(f"old ctrl = 0x{old_ctrl:016x}")
print(f"new src2 = R{src2}")
print(f"new src3 = R{src3}")
print(f"new inst = 0x{new_inst:016x}")
print(f"new ctrl = 0x{new_ctrl:016x}")

data = bytearray(infile.read_bytes())

old_bytes = struct.pack("<QQ", old_inst, old_ctrl)
new_bytes = struct.pack("<QQ", new_inst, new_ctrl)

count = data.count(old_bytes)
print(f"matched instruction count = {count}")

if count != 1:
    raise RuntimeError("Expected exactly one FFMA match.")

offset = data.find(old_bytes)
print(f"patch file offset = 0x{offset:x}")

data[offset:offset + 16] = new_bytes
outfile.write_bytes(data)

print(f"wrote {outfile}")
