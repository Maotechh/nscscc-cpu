# nscscc-cpu

本仓库的官方 `core_top` 已切换为 Scala/SpinalHDL 实现的 LA32R 乱序核。当前固定配置为取指 4、译码/重命名/分派 3、执行发射 4、写回 5、顺序提交 3；旧标量流水线不再参与生成。

当前架构、接口、生成方法、验证基线和接手注意事项统一记录在 [`docs/ooo-core.md`](docs/ooo-core.md)。

常用入口：

```bash
# WSL / Linux
make scala
make test
make python-test
make generate-core
make port-check
make lint
make yosys-check
make publish-check
```

`make generate-core` 先生成原始 Spinal RTL，再通过 `tools/core_top_gate.py package` 加入官方锁定的 `TLBNUM=32` 顶层合同。可提交的唯一 CPU RTL 是 `rtl/mycpu_top.v`，禁止手工修改生成文件。

Vivado 2023.2 在 Windows PowerShell 中运行：

```powershell
& 'D:\Xilinx\Vivado\2023.2\bin\vivado.bat' -mode batch `
  -source tools/ooo_core_top_synth.tcl `
  -tclargs rtl/mycpu_top.v build/vivado/core_top
```

比赛性能原始基准仍保存在 `baseline.txt`。当前 OoO 功能/综合基线见 `docs/ooo-core.md`，真实 FPGA 性能必须以远程评测结果为准。
