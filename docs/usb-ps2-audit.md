# USB / PS2 功能审计与修复路线（2026-07-25）

## 审计边界

- CPU 仓库：`dev`，审计期间只读。
- Linux 仓库：`/2022533109/liubushi/longxine/nscscc-linux-kernel`，
  `main@aa3888d6`，审计前后工作区保持干净。
- 已有 USB 证据仅覆盖内核构建/链接以及 Chiplab 全 SoC 实现
  `WNS=+0.011456 ns, TNS=0, DRC=0`；没有真实枚举、HID 事件或热插拔证据。
- 已有 PS/2 板级证据仅观察到 IRQ 23 探针；没有完整键盘命令链和输入事件证据。

## USB：优先级与修复计划

### P0：传输正确性和生命周期安全

1. `drivers/usb/host/ue11-hcd.c:928,959-967,1012-1038`
   当前接收路径接受任意 DATA0/DATA1，并无条件翻转 toggle。
   应按端点期望值校验 PID；重复包只排空，不能复制、完成 URB 或翻转 toggle；
   控制传输 status-IN 必须要求 DATA1。
2. `ue11h_urb_dequeue()`（约 1372、1395-1412）超时后会在 SIE 尚未停止时
   清除 active/giveback；迟到 IRQ 可能污染下一 URB。
   `endpoint_disable()`（约 1426-1440）还可能释放非空端点。
   修复时必须在硬件 idle/IRQ 清除前保持所有权，最好增加明确 abort/reset 流程。
3. 建立真实板级验收矩阵：10 次冷启动枚举、20 次热插拔、10 次
   `evtest` 热插拔；记录 VID/PID、描述符、IRQ 计数、输入事件和完整 `dmesg`。

### P1：错误处理、低功耗和 CDC

- 接通当前未使用的 RX_ERROR；补全 POWER、suspend/resume。
- 审查 APB 与 USB 时钟域的 bundled-data CDC，而不只同步控制位。
- 统一 RTL/manifest/Linux 的中断命名和编号。
- 扩展 `scripts/nscscc/validate-ue11-root-hub.sh`：当前只等待 1 秒且不验证 HID。

### P2：维护性

- 当前驱动约有 644 个 checkpatch error、1017 个 warning；应在 P0/P1 正确性稳定后
  分批重构，避免格式清理掩盖生命周期修复。

## PS/2：优先级与修复计划

### P0：中断契约和真实设备闭环

1. Chiplab 中 PS/2 为 `intrpt[5]`、USB 为 `intrpt[6]`；CPU 将
   `intrpt[7:0]` 映射到 ESTAT.IS[9:2]，所以应分别落到 IP7/IRQ23 和
   IP8/IRQ24。DTS 已使用 hwirq 7/8，但
   `arch/loongarch/loongson32/irq.c:30` 的 fallback 仍检查 IP5/IP6，
   分发 IRQ21/22。应修为 IP7→IRQ23、IP8→IRQ24，并增加跨仓库契约测试。
2. 给 `ps2_int` 增加与 USB 同等级的 CPU 时钟域两级同步器。
3. 用真实键盘验证 reset、ACK、BAT、scancode 和 `evtest` 事件链，
   并据结果判断是否可以移除 `atkbd.reset=0` workaround。

### P1：RTL 边界条件

- 完整复位 FIFO、TX/RX 状态和 sticky 状态。
- 将固定 20 位 timeout counter 改为由 `$clog2` 推导；当前
  `CLK_RATE/100` 在 uncore 超过约 104.8 MHz 时会溢出。
- 修复 FIFO 满且同周期 pop/push 时丢字节的问题。
- 为写入忙状态提供 backpressure 或可观测错误，而不是静默丢命令。
- 增加 reset/ACK/BAT、奇偶校验、timeout、FIFO 临界条件的自检 testbench。

### P2：集成完整性

- 将驱动整理到正式分支并补 DT schema。
- 若最终展示同时需要键盘和鼠标，再规划第二 PS/2 端口；当前单端口不应被描述为
  可同时支持两类设备。

## 结论

当前外围设备不能据已有日志宣称“功能完成”。优先顺序应为：
IRQ 契约修复 → USB URB/toggle 生命周期 → PS/2 同步和 reset →
真实硬件事件证据 → 低功耗、CDC 和代码风格清理。
