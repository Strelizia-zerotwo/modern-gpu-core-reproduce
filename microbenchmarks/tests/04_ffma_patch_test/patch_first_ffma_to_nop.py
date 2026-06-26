import re
import struct
from pathlib import Path

infile = Path("ffma_patch_kernel.cubin")
sassfile = Path("ffma_patch_kernel.sass")
outfile = Path("ffma_to_nop.cubin")

sass = sassfile.read_text()
lines = sass.splitlines()

target_line_idx = None
target_pc = None
old_inst = None
old_ctrl = None

for i, line in enumerate(lines):
    if "FFMA" in line:
        m_pc = re.search(r"/\*([0-9a-fA-F]+)\*/", line)
        m_inst = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", line)
        if not m_pc or not m_inst:
            continue

        # control word is usually on the next line
        if i + 1 >= len(lines):
            continue

        m_ctrl = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", lines[i + 1])
        if not m_ctrl:
            continue

        target_line_idx = i
        target_pc = int(m_pc.group(1), 16)
        old_inst = int(m_inst.group(1), 16)
        old_ctrl = int(m_ctrl.group(1), 16)
        break

if old_inst is None:
    raise RuntimeError("No FFMA instruction found in sass file.")

print(f"target PC   = 0x{target_pc:x}")
print(f"old inst    = 0x{old_inst:016x}")
print(f"old ctrl    = 0x{old_ctrl:016x}")
print(f"sass line   = {lines[target_line_idx].strip()}")

data = bytearray(infile.read_bytes())

old_bytes = struct.pack("<QQ", old_inst, old_ctrl)

# NOP encoding observed in sm_120 cubin
new_inst = 0x0000000000007918
new_ctrl = 0x000fc00000000000
new_bytes = struct.pack("<QQ", new_inst, new_ctrl)

count = data.count(old_bytes)
print(f"matched instruction count = {count}")

if count != 1:
    raise RuntimeError("Expected exactly one matched FFMA instruction. Stop to avoid patching wrong bytes.")

offset = data.find(old_bytes)
print(f"patch file offset = 0x{offset:x}")

data[offset:offset + 16] = new_bytes
outfile.write_bytes(data)

print(f"wrote {outfile}")
