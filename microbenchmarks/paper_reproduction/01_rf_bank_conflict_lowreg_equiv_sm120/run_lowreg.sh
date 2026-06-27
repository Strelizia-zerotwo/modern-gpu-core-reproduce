#!/usr/bin/env bash
set -euo pipefail

echo "========== build template =========="
nvcc -O3 -arch=sm_120 -cubin lowreg_kernel.cu -o lowreg_template.cubin

echo "========== resource usage =========="
cuobjdump --dump-resource-usage lowreg_template.cubin | tee lowreg_resource.txt

echo "========== dump template sass =========="
cuobjdump --dump-sass lowreg_template.cubin | tee lowreg_template.sass

echo "========== key template sass =========="
grep -n "IADD3\|I2FP.F32.U32\|CS2UR\|FFMA\|CS2R\|FADD\|STG" lowreg_template.sass || true

echo "========== build launcher =========="
nvcc launch_lowreg.cpp -L/usr/lib/wsl/lib -lcuda -o launch_lowreg

echo "========== generate low-reg equivalent cubins =========="
rm -f case_odd_odd.cubin case_even_odd.cubin case_even_even.cubin

python3 patch_lowreg.py 19 21 case_odd_odd.cubin
python3 patch_lowreg.py 18 21 case_even_odd.cubin
python3 patch_lowreg.py 18 20 case_even_even.cubin

echo "========== disassemble low-reg equivalent cubins =========="
for f in case_odd_odd.cubin case_even_odd.cubin case_even_even.cubin; do
    echo "----- $f -----"
    cuobjdump --dump-sass "$f" | grep -n "CS2UR\|FFMA\|CS2R\|FADD\|STG" || true
done

echo "========== run low-reg equivalent cubins =========="
echo "----- odd/odd equivalent: expected 459 -----"
./launch_lowreg case_odd_odd.cubin 459

echo "----- even/odd equivalent: expected 443 -----"
./launch_lowreg case_even_odd.cubin 443

echo "----- even/even equivalent: expected 442 -----"
./launch_lowreg case_even_even.cubin 442

echo "========== ALL DONE =========="
