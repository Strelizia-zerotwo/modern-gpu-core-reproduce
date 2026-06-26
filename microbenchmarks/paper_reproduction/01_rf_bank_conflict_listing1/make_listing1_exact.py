import re
import struct
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print("usage: python3 make_listing1_exact.py RX RY output.cubin")
    sys.exit(1)

RX = int(sys.argv[1])
RY = int(sys.argv[2])
outfile = Path(sys.argv[3])
infile = Path("listing1_template.cubin")

sass = subprocess.check_output(["cuobjdump", "--dump-sass", str(infile)], text=True)
lines = sass.splitlines()

def parse_inst_ctrl(i):
    line = lines[i]
    m_pc = re.search(r"/\*([0-9a-fA-F]+)\*/", line)
    m_inst = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", line)
    m_ctrl = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", lines[i + 1])
    if not (m_inst and m_ctrl):
        raise RuntimeError("parse failed near: " + line)
    return {
        "idx": i,
        "pc": int(m_pc.group(1), 16) if m_pc else -1,
        "line": line.strip(),
        "ctrl_line": lines[i + 1].strip(),
        "inst": int(m_inst.group(1), 16),
        "ctrl": int(m_ctrl.group(1), 16),
    }

cs2ur_idx = None
cs2r_idx = None

for i, line in enumerate(lines):
    if "CS2UR" in line and "SR_CLOCKLO" in line:
        cs2ur_idx = i
    if cs2ur_idx is not None and "CS2R" in line and "SR_CLOCKLO" in line:
        cs2r_idx = i
        break

if cs2ur_idx is None or cs2r_idx is None:
    raise RuntimeError("cannot find clock window")

# Need these ready registers:
# FFMA R11, R10, R12, R14
# FFMA R13, R16, RX, RY
target_float_regs = [10, 12, 14, 16, RX, RY]

i2fps = []
for i, line in enumerate(lines[:cs2ur_idx]):
    if "I2FP.F32.U32" in line:
        i2fps.append(parse_inst_ctrl(i))

if len(i2fps) < 6:
    raise RuntimeError(f"need at least 6 I2FP before clock, found {len(i2fps)}")

i2fps = i2fps[-6:]

ffmas_in_window = []
for i in range(cs2ur_idx + 1, cs2r_idx):
    if "FFMA" in lines[i]:
        ffmas_in_window.append(parse_inst_ctrl(i))

if len(ffmas_in_window) < 2:
    raise RuntimeError(f"need 2 FFMA inside clock, found {len(ffmas_in_window)}")

ffma1 = ffmas_in_window[0]
ffma2 = ffmas_in_window[1]

# Find first FADD after CS2R. We will patch it to:
# FADD R0, R11, R13
# This makes sink deterministic after we changed FFMA dst to R11/R13.
post_fadd = None
for i in range(cs2r_idx + 1, len(lines)):
    if "FADD" in lines[i]:
        post_fadd = parse_inst_ctrl(i)
        break

if post_fadd is None:
    raise RuntimeError("cannot find post-clock FADD to patch sink")

data = bytearray(infile.read_bytes())

def replace_exact(old_inst, old_ctrl, new_inst, new_ctrl, label):
    old_bytes = struct.pack("<QQ", old_inst, old_ctrl)
    new_bytes = struct.pack("<QQ", new_inst, new_ctrl)
    count = data.count(old_bytes)
    print(f"{label}: matched {count}")
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match")
    off = data.find(old_bytes)
    print(f"{label}: offset 0x{off:x}")
    data[off:off+16] = new_bytes

def patch_dst(inst, dst):
    inst &= ~(0xff << 16)
    inst |= (dst & 0xff) << 16
    return inst

def patch_3src_fp(inst, ctrl, dst, src1, src2, src3):
    # observed sm_120 FFMA/FADD-style:
    # dst  = inst bits 16..23
    # src1 = inst bits 24..31
    # src2 = inst bits 32..39
    # src3 for FFMA = ctrl low 8 bits
    inst &= ~(0xff << 16)
    inst |= (dst & 0xff) << 16

    inst &= ~(0xff << 24)
    inst |= (src1 & 0xff) << 24

    inst &= ~(0xff << 32)
    inst |= (src2 & 0xff) << 32

    ctrl = 0x000fe20000000000 | (src3 & 0xff)
    return inst, ctrl

def patch_fadd(inst, ctrl, dst, src1, src2):
    # FADD Rdst, Rsrc1, Rsrc2
    inst &= ~(0xff << 16)
    inst |= (dst & 0xff) << 16

    inst &= ~(0xff << 24)
    inst |= (src1 & 0xff) << 24

    inst &= ~(0xff << 32)
    inst |= (src2 & 0xff) << 32

    ctrl = 0x000fe20000000000
    return inst, ctrl

print("patch I2FP destination registers to:", target_float_regs)
for item, dst in zip(i2fps, target_float_regs):
    new_inst = patch_dst(item["inst"], dst)
    replace_exact(item["inst"], item["ctrl"], new_inst, item["ctrl"], f"I2FP_to_R{dst}")

# Listing 1 core
new_inst1, new_ctrl1 = patch_3src_fp(ffma1["inst"], ffma1["ctrl"], 11, 10, 12, 14)
replace_exact(ffma1["inst"], ffma1["ctrl"], new_inst1, new_ctrl1, "FFMA1_R11_R10_R12_R14")

new_inst2, new_ctrl2 = patch_3src_fp(ffma2["inst"], ffma2["ctrl"], 13, 16, RX, RY)
replace_exact(ffma2["inst"], ffma2["ctrl"], new_inst2, new_ctrl2, f"FFMA2_R13_R16_R{RX}_R{RY}")

# Fix sink: R0 = R11 + R13
new_fadd_inst, new_fadd_ctrl = patch_fadd(post_fadd["inst"], post_fadd["ctrl"], 0, 11, 13)
replace_exact(post_fadd["inst"], post_fadd["ctrl"], new_fadd_inst, new_fadd_ctrl, "POST_FADD_R0_R11_R13")

outfile.write_bytes(data)
print(f"wrote {outfile}")
