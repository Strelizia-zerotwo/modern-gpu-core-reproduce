# 2026-06-26 sm_120 Listing 1 复现进展记录

## 目标

今晚的目标是复现论文《Dissecting and Modeling the Architecture of Modern GPU Cores》中 Listing 1 的 register file bank conflict 微基准。

论文中的核心思想是：

- 用 `CLOCK/CS2UR` 和 `CLOCK/CS2R` 包围一小段 SASS；
- 手写或修改 SASS 指令和 control bits；
- 替换第二条 FFMA 的源寄存器 `R_X/R_Y`；
- 观察不同寄存器 bank 组合导致的 cycles 差异。

论文 Listing 1 的核心形式是：

```sass
CLOCK
NOP
FFMA R11, R10, R12, R14
FFMA R13, R16, R_X, R_Y
NOP
CLOCK

论文报告的结果为：

R19/R21 -> 5 cycles
R18/R21 -> 6 cycles
R18/R20 -> 7 cycles
当前环境

实验平台：

GPU: NVIDIA GeForce RTX 5070 Ti
Architecture: Blackwell
Target: sm_120
CUDA toolkit: 12.8
Driver: 591.74
OS: WSL2 Ubuntu

实验目录：

~/modern-gpu-core-reproduce/microbenchmarks/paper_reproduction/01_rf_bank_conflict_listing1
今晚完成的内容
1. 确认了 sm_120 cubin 可以被二进制 patch

由于公开版 CUAssembler 无法直接支持 sm_120 cubin，因此采用了二进制 patch 方法。

基本流程是：

CUDA C kernel
-> nvcc -arch=sm_120 -cubin
-> cuobjdump / nvdisasm 反汇编
-> 在 cubin 中定位 16-byte SASS encoding
-> patch 指令 word 和 control word
-> 使用 CUDA Driver API 加载 patched cubin 执行

这个流程本身已经跑通。

2. 成功 patch 出了 Listing 1 的核心 FFMA 寄存器形状

生成了三组 patched cubin：

listing1_R19_R21.cubin
listing1_R18_R21.cubin
listing1_R18_R20.cubin

反汇编结果中，clock window 里成功出现了三组目标 FFMA：

CS2UR UR6, SR_CLOCKLO
FFMA R11, R10, R12, R14
FFMA R13, R16, R19, R21
CS2R R2, SR_CLOCKLO
CS2UR UR6, SR_CLOCKLO
FFMA R11, R10, R12, R14
FFMA R13, R16, R18, R21
CS2R R2, SR_CLOCKLO
CS2UR UR6, SR_CLOCKLO
FFMA R11, R10, R12, R14
FFMA R13, R16, R18, R20
CS2R R2, SR_CLOCKLO

说明 FFMA 的部分寄存器字段 patch 是有效的。

3. 编写了 CUDA Driver API 运行器

编写了 launch_listing1.cpp，用于直接加载 patched cubin 并运行：

cuModuleLoad
cuModuleGetFunction
cuLaunchKernel
cuMemcpyDtoH

这一步也能正常用于启动 cubin。

没有成功的地方
1. 没有复现论文的 5/6/7 cycles

当前最终运行结果不是论文中的：

5 / 6 / 7 cycles

而是三组都测到了：

3 / 3 / 3 cycles

因此不能认为已经复现 Listing 1 的 register file bank conflict 现象。

2. sink 数值不正确

运行时 sink 出现随机大数、负数、0 等异常值。

这说明当前 patched cubin 的结果输出路径不可靠。

原因大概率是：

原始模板的输出路径是围绕原始 FFMA 目标寄存器设计的；
patch 后把 FFMA 目标寄存器改成了 R11/R13；
但是后续 FADD/STG 并没有被可靠地同步改成读取 R11/R13；
因此写回的 sink 并不是两条目标 FFMA 的真实结果。

所以当前结果不能作为有效实验数据。

3. 当前 clock window 不完全等同于论文 Listing 1

论文 Listing 1 中有：

CLOCK
NOP
FFMA
FFMA
NOP
CLOCK

当前实际窗口更接近：

CS2UR
FFMA
FFMA
CS2R

缺少论文中的前后 NOP，并且 control bits 也不是论文环境下的手写 control bits。

这会直接影响测得 cycles。

4. binary patch 方法目前不够稳

今晚暴露出几个问题：

1. 只 patch FFMA 源寄存器相对可行；
2. patch FFMA 目标寄存器会影响后续输出路径；
3. patch FADD / sink 路径不可靠；
4. 模板 cubin 的 REG 数、control bits、reuse bits 都可能影响运行正确性；
5. sm_120 的 control word 不能靠猜。

因此当前路线不能继续硬修。

当前结论

今晚没有完成论文 Listing 1 的成功复现。

但完成了以下基础能力验证：

1. sm_120 cubin 可以生成和反汇编；
2. sm_120 cubin 可以被二进制 patch；
3. FFMA 寄存器字段可以被 patch 出目标 SASS 形状；
4. patched cubin 可以通过 CUDA Driver API 加载运行；
5. 当前 naive binary patch 方案不足以可靠复现 Listing 1。
下一步正确路线

下一步不应该继续修当前脚本，而应该换成更稳的实验设计。

建议路线：

路线 A：只 patch 源寄存器，不 patch 目标寄存器

重新设计模板，使编译器自己生成正确 sink 输出路径。

目标：

FFMA R0, R10, R12, R14
FFMA R9, R16, RX, RY
FADD R9, R0, R9
STG sink, R9

这样只 patch 第二条 FFMA 的 RX/RY，不修改 FFMA 目标寄存器，避免 sink 乱。

路线 B：先验证 sink，再测 cycles

每次 patch 后先验证数学结果，例如：

10 * 12 + 14 = 134
16 * 19 + 21 = 325
sum = 459

只有 sink 正确，cycles 才有意义。

路线 C：补完整 NOP 和 control bits

在 sink 正确之后，再加入论文 Listing 1 的完整窗口：

CS2UR
NOP
FFMA
FFMA
NOP
CS2R

并系统比较不同 control bits 对 cycles 的影响。

路线 D：记录失败原因

当前失败不是无效工作，而是确认了一个重要事实：

在 sm_120 / Blackwell 上，不能只靠 naive binary patch 目标寄存器来复现论文 Listing 1。
必须保持输出路径正确，并严格控制 control bits。
当前状态

当前目录保留为失败但有价值的实验记录：

microbenchmarks/paper_reproduction/01_rf_bank_conflict_listing1

当前结果不能写成“复现成功”，只能写成：

Attempted Listing 1 reproduction on sm_120.
Successfully patched target FFMA SASS shape.
Runtime correctness and expected cycle deltas were not achieved.
