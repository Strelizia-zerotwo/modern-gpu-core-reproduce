import re
import struct
import subprocess
import sys
from pathlib import Path

def die(msg):
    print("[FAIL]", msg)
    sys.exit(1)

if len(sys.argv) != 4:
    print("usage: python3 patch_lowreg.py RX_VALUE RY_VALUE output.cubin")
    sys.exit(1)

RX_VAL = int(sys.argv[1])
RY_VAL = int(sys.argv[2])
outfile = Path(sys.argv[3])

infile = Path("lowreg_template.cubin")
if not infile.exists():
    die("lowreg_template.cubin not found")

sass = subprocess.check_output(["cuobjdump", "--dump-sass", str(infile)], text=True)
lines = sass.splitlines()

def parse_inst_ctrl(i):
    line = lines[i]
    m_inst = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", line)
    m_ctrl = re.search(r"/\*\s*(0x[0-9a-fA-F]+)\s*\*/", lines[i + 1])
    if not (m_inst and m_ctrl):
        die("parse failed near: " + line)
    return {
        "idx": i,
        "line": line.strip(),
        "inst": int(m_inst.group(1), 16),
        "ctrl": int(m_ctrl.group(1), 16),
    }

def parse_ffma(line):
    s = line.replace(".reuse", "")
    m = re.search(r"FFMA\s+R(\d+),\s+R(\d+),\s+R(\d+),\s+R(\d+)", s)
    if not m:
        die("cannot parse FFMA: " + line)
    return tuple(int(x) for x in m.groups())

def parse_iadd_value(line):
    m = re.search(r"IADD3\s+R(\d+),.*?,\s*(0x[0-9a-fA-F]+|\d+),\s*RZ", line)
    if not m:
        return None
    reg = int(m.group(1))
    imm_s = m.group(2)
    val = int(imm_s, 16) if imm_s.lower().startswith("0x") else int(imm_s)
    return reg, val

def parse_i2fp(line):
    s = line.replace(".reuse", "")
    m = re.search(r"I2FP\.F32\.U32\s+R(\d+),\s+R(\d+)", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

cs2ur_idx = None
cs2r_idx = None

for i, line in enumerate(lines):
    if "CS2UR" in line and "SR_CLOCKLO" in line:
        cs2ur_idx = i
    if cs2ur_idx is not None and "CS2R" in line and "SR_CLOCKLO" in line:
        cs2r_idx = i
        break

if cs2ur_idx is None or cs2r_idx is None:
    die("cannot find CS2UR -> CS2R window")

print(f"[INFO] clock window lines: {cs2ur_idx} -> {cs2r_idx}")

# Build value -> float register map from the original template.
int_reg_to_value = {}

for line in lines[:cs2ur_idx]:
    if "IADD3" not in line:
        continue
    parsed = parse_iadd_value(line)
    if parsed is None:
        continue
    reg, val = parsed
    if val in [10, 12, 14, 16, 18, 19, 20, 21]:
        int_reg_to_value[reg] = val

value_to_float_reg = {}

for line in lines[:cs2ur_idx]:
    if "I2FP.F32.U32" not in line:
        continue
    parsed = parse_i2fp(line)
    if parsed is None:
        continue
    fdst, isrc = parsed
    if isrc in int_reg_to_value:
        value = int_reg_to_value[isrc]
        value_to_float_reg[value] = fdst

needed = [10, 12, 14, 16, 18, 19, 20, 21]
missing = [v for v in needed if v not in value_to_float_reg]

if missing:
    print("[DEBUG] pre-clock SASS:")
    for line in lines[:cs2ur_idx]:
        if "IADD3" in line or "I2FP" in line:
            print(line)
    die(f"missing value producers: {missing}")

print("[INFO] original value -> float reg:")
for v in needed:
    print(f"  value {v} -> R{value_to_float_reg[v]}")

ffmas = []
for i in range(cs2ur_idx + 1, cs2r_idx):
    if "FFMA" in lines[i]:
        item = parse_inst_ctrl(i)
        item["regs"] = parse_ffma(item["line"])
        ffmas.append(item)

if len(ffmas) < 2:
    die(f"need two FFMA inside clock window, found {len(ffmas)}")

# Find variable FFMA: original should be 16*18+20.
r16 = value_to_float_reg[16]
r18 = value_to_float_reg[18]
r20 = value_to_float_reg[20]

variable_ffma = None
fixed_ffma = None

for item in ffmas:
    dst, s1, s2, s3 = item["regs"]
    if (s1, s2, s3) == (r16, r18, r20):
        variable_ffma = item
    else:
        fixed_ffma = item

if variable_ffma is None:
    print("[DEBUG] FFMA in clock window:")
    for item in ffmas:
        print("  ", item["line"])
    die("cannot find variable FFMA with sources value16,value18,value20")

print("[INFO] variable FFMA before:", variable_ffma["line"])
if fixed_ffma:
    print("[INFO] fixed FFMA kept:", fixed_ffma["line"])

data = bytearray(infile.read_bytes())

def replace_exact(old_inst, old_ctrl, new_inst, new_ctrl, label):
    old_bytes = struct.pack("<QQ", old_inst, old_ctrl)
    new_bytes = struct.pack("<QQ", new_inst, new_ctrl)

    if old_inst == new_inst and old_ctrl == new_ctrl:
        print(f"[PATCH] {label}: no change needed")
        return

    count = data.count(old_bytes)
    print(f"[PATCH] {label}: matched {count}")

    if count != 1:
        die(f"{label}: expected exactly one match")

    off = data.find(old_bytes)
    print(f"[PATCH] {label}: offset 0x{off:x}")
    data[off:off+16] = new_bytes

def patch_ffma_sources_keep_dst(inst, ctrl, src1, src2, src3):
    # sm_120 observed FFMA:
    # dst stays unchanged
    # src1 = inst bits 24..31
    # src2 = inst bits 32..39
    # src3 = ctrl low 8 bits
    inst &= ~(0xff << 24)
    inst |= (src1 & 0xff) << 24

    inst &= ~(0xff << 32)
    inst |= (src2 & 0xff) << 32

    ctrl &= ~0xff
    ctrl |= (src3 & 0xff)

    return inst, ctrl

src1 = value_to_float_reg[16]
src2 = value_to_float_reg[RX_VAL]
src3 = value_to_float_reg[RY_VAL]

print(f"[INFO] patch variable FFMA sources to values 16,{RX_VAL},{RY_VAL}")
print(f"[INFO] physical sources: R{src1}, R{src2}, R{src3}")

new_inst, new_ctrl = patch_ffma_sources_keep_dst(
    variable_ffma["inst"],
    variable_ffma["ctrl"],
    src1,
    src2,
    src3
)

replace_exact(
    variable_ffma["inst"],
    variable_ffma["ctrl"],
    new_inst,
    new_ctrl,
    f"variable_FFMA_sources_16_{RX_VAL}_{RY_VAL}"
)

outfile.write_bytes(data)
print(f"[OK] wrote {outfile}")
