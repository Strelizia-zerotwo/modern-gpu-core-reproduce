import re
import struct
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print("usage: python3 patch_second_ffma_src_regs.py src2_reg src3_reg output.cubin")
    print("example: python3 patch_second_ffma_src_regs.py 6 9 ffma2_s2_6_s3_9.cubin")
    sys.exit(1)

src2 = int(sys.argv[1])
src3 = int(sys.argv[2])
outfile = Path(sys.argv[3])

infile = Path("two_ffma_ready_kernel.cubin")
sassfile = Path("two_ffma_ready_kernel.sass")

sass = sassfile.read_text()
lines = sass.splitlines()

ffmas = []

for i, line in enumerate(lines):
    if "FFMA" in line:
        m_pc = re.search(r"/\*([0-9a-fA-F]+)\*/", line)
        m_inst = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", line)
        if i + 1 >= len(lines):
            continue
        m_ctrl = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", lines[i + 1])
        if m_pc and m_inst and m_ctrl:
            ffmas.append({
                "line": line.strip(),
                "ctrl_line": lines[i + 1].strip(),
                "pc": int(m_pc.group(1), 16),
                "inst": int(m_inst.group(1), 16),
                "ctrl": int(m_ctrl.group(1), 16),
            })

if len(ffmas) < 2:
    raise RuntimeError(f"Expected at least two FFMA instructions, found {len(ffmas)}.")

target = ffmas[1]   # 第二条 FFMA

old_inst = target["inst"]
old_ctrl = target["ctrl"]

print("target second FFMA:")
print(target["line"])
print(target["ctrl_line"])
print(f"target PC = 0x{target['pc']:x}")

# Observed sm_120 FFMA encoding form:
#   FFMA dst, src1, src2, src3
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
    raise RuntimeError("Expected exactly one second FFMA match.")

offset = data.find(old_bytes)
print(f"patch file offset = 0x{offset:x}")

data[offset:offset + 16] = new_bytes
outfile.write_bytes(data)

print(f"wrote {outfile}")
