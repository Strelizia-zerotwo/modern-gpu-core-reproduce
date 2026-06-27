# RTX 5070 Ti / SM120 模拟器验证日志：Rodinia backprop

日期：2026-06-28  
仓库路径：`~/modern-gpu-simulator-micro-2025/simulator-remodeled`  
验证目标：使用真实 RTX 5070 Ti Laptop GPU 运行 Rodinia backprop，并与 SM120_RTX5070_TI 模拟器结果对比周期数误差。

---

## 1. 实验环境

- GPU：NVIDIA GeForce RTX 5070 Ti Laptop GPU
- Compute Capability：12.0
- CUDA：12.8
- 模拟器配置目录：`gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM120_RTX5070_TI`
- job launcher 配置别名：`RTX5070_TI`
- benchmark suite：`rodinia_2.0-ft`
- 本次实际完成对比的 benchmark：`backprop-rodinia-2.0-ft`
- 输入参数：`4096`

---

## 2. 实验中遇到的问题与修复记录

### 2.1 编译依赖问题

遇到过的问题包括：

```text
protoc: No such file or directory
bison: No such file or directory
/usr/bin/ld: cannot find -lGL
```

对应修复：

```bash
sudo apt update
sudo apt install -y protobuf-compiler libprotobuf-dev
sudo apt install -y bison flex
sudo apt install -y libgl1-mesa-dev libglu1-mesa-dev mesa-common-dev
```

### 2.2 `std::function` 未声明

编译时报：

```text
error: ‘std::function’ has not been declared
```

修复：

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

HEADER=$(find ./gpu-simulator/gpgpu-sim/src -name "ldst_unit_sm.h" | head -n 1)
grep -q "#include <functional>" "$HEADER" || sed -i '1i#include <functional>' "$HEADER"
```

### 2.3 Python 缺 psutil

采 trace 时遇到：

```text
ModuleNotFoundError: No module named 'psutil'
```

由于 Ubuntu Python 是 externally managed，不建议使用 `pip --break-system-packages`，直接安装系统包：

```bash
sudo apt update
sudo apt install -y python3-psutil
```

### 2.4 job launcher 本地调度问题

`run_simulations.py` 可以把 10 个 Rodinia job 加入队列，但本地 ProcMan 没有真正生成 `.o1 ~ .o10` 输出文件，`get_stats.py` 显示全部为 NA。因此本次没有继续依赖 job launcher，而是改用 direct simulation：

```bash
./gpu-simulator/bin/release/accel-sim.out   -trace <dynamic_trace.pb>   -config ./gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM120_RTX5070_TI/gpgpusim.config   -config ./gpu-simulator/configs/tested-cfgs/SM120_RTX5070_TI/trace.config
```

### 2.5 `_ZTI12cache_config` 符号错误

direct simulation 初次运行时报：

```text
undefined symbol: _ZTI12cache_config
```

含义是 `cache_config` 的 RTTI 符号找不到，通常是旧 `.o/.so` 和新编译产物混用。最终通过清理 simulator 编译产物并完整重编解决：

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

rm -rf ./gpu-simulator/bin
rm -rf ./gpu-simulator/build
rm -rf ./gpu-simulator/lib
rm -rf ./gpu-simulator/gpgpu-sim/build
rm -rf ./gpu-simulator/gpgpu-sim/lib

HEADER=$(find ./gpu-simulator/gpgpu-sim/src -name "ldst_unit_sm.h" | head -n 1)
grep -q "#include <functional>" "$HEADER" || sed -i '1i#include <functional>' "$HEADER"

export CUDA_INSTALL_PATH=/usr/local/cuda
export CUDA_HOME=/usr/local/cuda
export CUDA_PATH=/usr/local/cuda
export PATH=/usr/local/cuda/bin:/usr/bin:/bin
unset LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64

make -j"$(nproc)" -C ./gpu-simulator   CUDA_INSTALL_PATH=/usr/local/cuda   CUDA_HOME=/usr/local/cuda   CUDA_PATH=/usr/local/cuda   | tee ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/rebuild_simulator_clean.log

ls -lh ./gpu-simulator/bin/release/accel-sim.out
```

### 2.6 Nsight Compute 权限问题

硬件测量初次运行 NCU 时遇到：

```text
ERR_NVGPUCTRPERM
```

含义是当前用户没有权限访问 NVIDIA GPU performance counters。WSL2 下需要在 Windows 宿主机 NVIDIA Control Panel 中开启：

```text
Desktop → Enable Developer Settings
Developer → Manage GPU Performance Counters
Allow access to the GPU performance counters to all users
```

然后在 Windows PowerShell 执行：

```powershell
wsl --shutdown
```

重新打开 WSL 后，NCU 正常采集。

---

## 3. 完整复现实验教程

### 3.1 进入仓库并设置环境

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

export CUDA_INSTALL_PATH=/usr/local/cuda
export CUDA_HOME=/usr/local/cuda
export CUDA_PATH=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
```

### 3.2 编译 Rodinia

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

source ./gpu-app-collection/src/setup_environment

make -j"$(nproc)" -C ./gpu-app-collection/src rodinia_2.0-ft   > ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/build_rodinia.log 2>&1

make -C ./gpu-app-collection/src data   > ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/build_data.log 2>&1
```

### 3.3 采集 Rodinia trace

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

export CUDA_INSTALL_PATH=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH

./util/tracer_nvbit/run_hw_trace.py -B rodinia_2.0-ft -D 0   > ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/trace_rodinia.log 2>&1

tail -80 ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/trace_rodinia.log
```

确认 trace 数量：

```bash
find ./hw_run/traces/device-0/12.8 -name dynamic_trace.pb | wc -l
```

本次结果为 10 个 Rodinia benchmark trace。

### 3.4 direct simulation 跑 backprop

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

unset LD_LIBRARY_PATH
GPGPU_LIB=$(find "$PWD/gpu-simulator/gpgpu-sim/lib" -type d -path "*release" | head -n 1)
SIM_LIB=$(find "$PWD/gpu-simulator/lib" -type d -path "*release" | head -n 1)
export LD_LIBRARY_PATH="$SIM_LIB:$GPGPU_LIB:/usr/local/cuda/lib64"

TRACE_PB=$(find ./hw_run/traces/device-0/12.8/backprop-rodinia-2.0-ft -name dynamic_trace.pb | head -n 1)

echo "TRACE_PB=$TRACE_PB"

./gpu-simulator/bin/release/accel-sim.out   -trace "$TRACE_PB"   -config ./gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM120_RTX5070_TI/gpgpusim.config   -config ./gpu-simulator/configs/tested-cfgs/SM120_RTX5070_TI/trace.config   | tee ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/direct_backprop_sim.log
```

模拟结束判断标志：

```text
GPGPU-Sim: *** exit detected ***
```

### 3.5 提取模拟器结果

```bash
grep -E "kernel_name|gpu_tot_sim_cycle|gpu_tot_sim_insn|gpu_tot_ipc|gpu_ipc|gpgpu_simulation_time|GPGPU-Sim: \*\*\* exit"   ~/modern-gpu-core-reproduce/validation/5070ti_sm120/logs/direct_backprop_sim.log
```

本次模拟结果：

```text
kernel_name = _Z22bpnn_layerforward_CUDAPfS_S_S_ii___0
gpu_ipc = 485.3850
gpu_tot_sim_cycle = 6810
gpu_tot_sim_insn = 3305472
gpu_tot_ipc = 485.3850

kernel_name = _Z24bpnn_adjust_weights_cudaPfiS_iS_S____0
gpu_ipc = 536.2836
gpu_tot_sim_cycle = 20010
gpu_tot_sim_insn = 10384416
gpu_tot_ipc = 518.9613
```

### 3.6 硬件端用 Nsight Compute 测量

```bash
cd ~/modern-gpu-simulator-micro-2025/simulator-remodeled

BACKPROP_EXE=./gpu-app-collection/bin/12.8/release/backprop-rodinia-2.0-ft

ncu   --target-processes all   --metrics sm__cycles_elapsed.avg,sm__inst_executed.sum,gpu__time_duration.sum   --csv   --page raw   --log-file ~/modern-gpu-core-reproduce/validation/5070ti_sm120/hw_backprop_ncu.csv   "$BACKPROP_EXE" 4096
```

查看硬件结果：

```bash
sed -n '1,220p' ~/modern-gpu-core-reproduce/validation/5070ti_sm120/hw_backprop_ncu.csv
```

或者只抓关键字段：

```bash
grep -E "Kernel Name|bpnn_layerforward|bpnn_adjust_weights|sm__cycles_elapsed.avg|sm__inst_executed.sum|gpu__time_duration.sum"   ~/modern-gpu-core-reproduce/validation/5070ti_sm120/hw_backprop_ncu.csv
```

---

## 4. 本次实验结果

### 4.1 Simulator 结果

| Kernel | sim cycles | sim instructions | sim IPC |
|---|---:|---:|---:|
| `bpnn_layerforward_CUDA` | 6810 | 3,305,472 | 485.3850 |
| `bpnn_adjust_weights_cuda` | 20010 | 10,384,416 | 536.2836 / total 518.9613 |

### 4.2 Hardware / NCU 结果

| Kernel | hw cycles `sm__cycles_elapsed.avg` | hw instructions `sm__inst_executed.sum` | kernel time `gpu__time_duration.sum` |
|---|---:|---:|---:|
| `bpnn_layerforward_CUDA` | 8093.70 | 151,552 | 8768 ns |
| `bpnn_adjust_weights_cuda` | 17890.30 | 221,251 | 19296 ns |

### 4.3 周期误差

误差公式：

```text
APE = |sim_cycles - hw_cycles| / hw_cycles × 100%
```

| Kernel | sim cycles | hw cycles | APE |
|---|---:|---:|---:|
| `bpnn_layerforward_CUDA` | 6810 | 8093.70 | 15.86% |
| `bpnn_adjust_weights_cuda` | 20010 | 17890.30 | 11.85% |

平均 per-kernel MAPE：

```text
Mean APE = 13.85%
```

如果直接把两个 kernel 的周期相加：

```text
sim total cycles = 6810 + 20010 = 26820
hw total cycles  = 8093.70 + 17890.30 = 25984.00
total APE = 3.22%
```

注意：total APE 会受到正负误差抵消影响，因此报告中应该以 per-kernel MAPE = 13.85% 为主。

---

## 5. 指标解释

### 5.1 主指标：cycles

本实验最应该比较的是：

```text
simulator: gpu_tot_sim_cycle
hardware : sm__cycles_elapsed.avg
```

这是模拟器性能验证中最直接的周期数对比。

### 5.2 辅助指标：instructions

模拟器输出：

```text
gpu_tot_sim_insn
```

NCU 输出：

```text
sm__inst_executed.sum
```

这两个值在本实验中口径明显不同，不能直接作为主要误差指标。例如第一个 kernel：

```text
sim instructions = 3,305,472
hw instructions  = 151,552
```

差距约 21.8 倍，因此这里只作为辅助检查，不作为主要精度结论。

### 5.3 辅助指标：kernel time

NCU 的：

```text
gpu__time_duration.sum
```

表示硬件 kernel 执行时间。它可以辅助说明硬件实际执行耗时，但与模拟器的周期数相比，频率、boost、测量口径都会带来额外变量，因此不作为主指标。

---

## 6. 可写进报告的结论

本实验使用 RTX 5070 Ti Laptop GPU 对 MICRO 2025 remodeled simulator 的 SM120_RTX5070_TI 配置进行初步验证。实验选取 Rodinia 2.0-ft 中的 backprop benchmark，输入规模为 4096。首先在真实 GPU 上使用 NVBit tracer 采集 SASS trace，然后使用 trace-driven simulator 进行模拟，最后通过 Nsight Compute 在真实硬件上测量 `sm__cycles_elapsed.avg`。

结果显示，backprop 中两个 kernel 的周期误差分别为 15.86% 和 11.85%，per-kernel MAPE 为 13.85%。该误差量级与原论文 remodeled simulator 的误差范围基本一致。需要注意的是，如果将两个 kernel 的周期直接相加，总周期误差仅为 3.22%，但这是由于两个 kernel 的误差方向相反产生了抵消，因此不能作为主要结论。更合理的报告方式是按 kernel 分别计算 APE，并报告 per-kernel MAPE。
