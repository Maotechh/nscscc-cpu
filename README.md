# nscscc-cpu

2026 龙芯杯团体赛 CPU 设计，基于 openLA500 五级流水线基线。

## 目录结构

```
nscscc-cpu/
├── rtl/                  # CPU RTL 源码（21 个 Verilog + csr.h）
│   ├── mycpu_top.v       # 顶层模块，chiplab core_top 接口
│   ├── if_stage.v        # 取指阶段（含 PC 生成）
│   ├── id_stage.v        # 译码阶段
│   ├── exe_stage.v       # 执行阶段（ALU）
│   ├── mem_stage.v       # 访存阶段
│   ├── wb_stage.v        # 写回阶段
│   ├── icache.v          # 指令 Cache（8KB, 2-way）
│   ├── dcache.v          # 数据 Cache（8KB, 2-way）
│   ├── btb.v             # 分支目标缓冲（32 项）
│   ├── tlb_entry.v       # TLB（32 项）
│   ├── csr.v             # 控制状态寄存器
│   ├── alu.v / mul.v / div.v  # 运算单元
│   ├── addr_trans.v      # 地址转换
│   ├── axi_bridge.v      # AXI 总线桥
│   ├── regfile.v         # 寄存器文件
│   ├── perf_counter.v    # 性能计数器
│   └── tools.v           # 工具函数
├── soc/                  # SoC 集成配置
│   ├── soc_top.v         # SoC 顶层（CPU + AXI crossbar + confreg + RAM + UART）
│   ├── soc_config.vh     # 功能/性能测试切换、DDR 开关
│   ├── confreg.v         # 配置寄存器（LED、数码管、虚拟 UART、计数器）
│   └── config.h          # C 头文件
├── sw/                   # 软件
│   ├── start.S           # Linux 内核启动桩（UART 初始化 + 跳转）
│   ├── regdef.h          # 寄存器定义
│   └── nscscc_perf/      # 性能测试基准程序（20 个）
│       ├── bench/coremark/
│       ├── bench/dhrystone/
│       ├── bench/stream_copy/
│       ├── bench/sha/
│       ├── bench/crc32/
│       └── ...
└── xilinx_ip/            # Xilinx IP 核
    └── sram/             # SRAM IP（tagv_sram, data_bank_sram）
```

## 当前状态

| 项目 | 状态 |
|------|------|
| 功能测试（58 项） | ✅ PASS（3A00003A） |
| 性能测试（20 项） | ⏳ 待运行 |
| Linux 启动 | ✅ PMON + TFTP + Linux（实验箱 SoC） |
| 频率 | cpu_clk = 32.727 MHz |
| Cache | 8KB I-Cache + 8KB D-Cache（完全 LUT RAM） |
| 资源 | LUT 15.5%, FF 7.4%, BRAM 0%, DSP 0% |

## 使用方法

将这些文件放入 chiplab 的对应位置：

```bash
cp rtl/*.v $CHIPLAB_HOME/IP/myCPU/
cp rtl/csr.h $CHIPLAB_HOME/IP/myCPU/
cp soc/* $CHIPLAB_HOME/chip/soc_demo/nscscc-team/
cp -r xilinx_ip/* $CHIPLAB_HOME/IP/myCPU/xilinx_ip/
cp -r sw/* $CHIPLAB_HOME/software/examples/
```

然后按 chiplab 标准流程构建。

## 协作注意事项

- 修改 RTL 后先在本地仿真通过，再 push
- `soc_config.vh` 的 `RUN_FUNC_TEST` / `RUN_PERF_TEST` 互斥，只能开一个
- 综合前检查 `SIMU_USE_DDR`：仿真=0（片上 BRAM），上板=1（DDR3）
- 工具链：loongarch32r-linux-gnusf-（GCC 8.3.0）
- Vivado：2023.2，约束文件 soc_lite.xdc 不允许修改
