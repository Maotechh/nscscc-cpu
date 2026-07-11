# Component replacement overlay 行为合同

## 目标

以 `reference/manifest.lock` 锁定的 `a158aa8` 22-file RTL 为不可漂移 base，只替换结构化 spec 明确列出的一个或多个 component 文件，为 golden recovery 和后续逐模块 Spinal 迁移提供可执行的 chiplab diagnostic DUT。

本合同不晋升新的 golden，不改变默认 locked baseline 命令，也不允许 mixed DUT 冒充 baseline PASS。

## CLI 合同

`chiplab-overlay` 增加：

```text
--replacement-spec <repo-relative-json>
--source-head <full-40-character-sha>
```

规则：

1. 两个参数必须同时出现，并且只允许与 `--dut-source mixed --diagnostic` 组合。
2. mixed base 固定为 `team_golden_candidate`；使用 replacement 时禁止 `--candidate-commit` override。
3. `--source-head` 必须是完整 40 位 SHA，并且逐字等于当前 HEAD；入口与写 manifest 前各复验一次。
4. spec 与 replacement source 必须都是该 source HEAD 中的普通 Git blob；不读取或回退到未提交工作树内容。staged、untracked、文件模式或忽略行尾空白后仍存在的语义 diff 均失败；Windows/WSL 对同一 checkout 的纯 CRLF 归一化差异允许通过，但原始 status 条目数和 `eol_normalization_only` 必须写入 manifest。
5. 任一失败在开始时删除同 iteration 的旧 overlay report，不能留下可复用的旧 diagnostic/PASS。
6. overlay 与 smoke 必须使用同一 Linux `CHIPLAB_WORK_ROOT`。两者同时获取 `OUT_DIR` 和 work root 下的 iteration lock；任一活动命令存在时，另一命令不得 reset 或消费同一 DUT。
7. `OUT_DIR` 与 `CHIPLAB_WORK_ROOT` 必须是互不相同、互非祖先/后代的目录；在创建锁或 reset worktree 前检查，拒绝证据目录与可删除工作区发生别名。

统一 Make 入口示例（在 WSL/Linux 中执行）：

```bash
SOURCE_HEAD="$(git rev-parse HEAD)"
ITERATION_ID="<iteration-id>"
make chiplab-doctor \
  OUT_DIR=/tmp/nscscc-component-overlay \
  CHIPLAB_REFERENCE=/opt/chiplab-reference

make chiplab-overlay \
  OUT_DIR=/tmp/nscscc-component-overlay \
  CHIPLAB_WORK_ROOT=/tmp/nscscc-component-work \
  CHIPLAB_REFERENCE=/opt/chiplab-reference \
  ITERATION_ID="$ITERATION_ID" \
  DUT_SOURCE=mixed DIAGNOSTIC=1 \
  REPLACEMENT_SPEC=tests/fixtures/component-overlay/identity.json \
  SOURCE_HEAD="$SOURCE_HEAD"

make rtl-smoke \
  OUT_DIR=/tmp/nscscc-component-overlay \
  CHIPLAB_WORK_ROOT=/tmp/nscscc-component-work \
  ITERATION_ID="$ITERATION_ID" \
  DIAGNOSTIC=1
```

doctor、overlay、smoke 必须共用 `OUT_DIR`；doctor 与 overlay 必须共用 `CHIPLAB_REFERENCE`；overlay 与 smoke 必须共用 `CHIPLAB_WORK_ROOT` 和 `ITERATION_ID`。`DIAGNOSTIC` 只接受空、`0` 或 `1`。spec、replacement 和 evaluator 提交后工作树必须 clean，再运行 doctor/overlay/smoke。

若进程被 `SIGKILL` 或机器断电，fail-closed lock 文件可能保留。只能在人工核对记录的 PID 已不存在且没有 overlay/smoke 进程后删除对应 `.locks/iterations/<iteration-id>.lock`；不得由脚本按时间自动清锁。

## Spec schema

```json
{
  "schema_version": 1,
  "replacements": [
    {
      "target": "rtl/icache.v",
      "source": "reference/component-replacements/icache.v",
      "base_sha256": "<64 lowercase hex>",
      "replacement_sha256": "<64 lowercase hex>"
    }
  ]
}
```

- 顶层和 entry 不接受未知字段。
- replacement 数量至少 1，target/source 均不得重复。
- `target` 必须逐字匹配 `golden-rtl-files.lock` 中的 `.v` 路径；不能替换 header、license、dead/backup 文件。
- `source` 必须是规范化 repo-relative POSIX 路径，无空段、`.`、`..`、反斜杠或绝对路径；basename 必须与 target 相同。
- source Git tree mode 只能是 `100644` 或 `100755` 普通 blob；拒绝 `120000` symlink、submodule、目录和 path traversal。
- `base_sha256` 必须匹配 `a158aa8:<target>`；`replacement_sha256` 必须匹配 `<source-head>:<source>`。
- replacement 内只允许 literal `` `include "mycpu.h"``；拒绝绝对/相对其他 include 和宏展开 include。spec 不能引入额外 support HDL。
- replacement 禁止本地 `` `define/`undef``、token-paste、历史 base 未引用的新宏、`$readmemh/$readmemb`、文件 I/O、dump/random、plusargs、`$system` 和 DPI 等未绑定外部依赖。未来若活动功能确需此类输入，必须先扩展 spec，逐项记录宏值或路径、Git blob、SHA256 和 overlay target。

## 导出与 overlay 不变量

1. 先按 locked allowlist 导出 22 个 base Git blob，再对 spec target 做一对一替换；最终 target 文件数仍精确为 22。
2. 每个文件 entry 标记 `source_kind=golden|replacement`。replacement entry 同时记录 base source/hash、replacement source/hash、spec source/hash。
3. `IP/myCPU` 中允许的 HDL exact union 只包含 22 个目标 basename 与锁定 `mycpu.h`；递归枚举子目录，任何额外 `.v/.sv/.vh/.h` 都失败。
4. manifest 中 overlay path 必须精确为 `IP/myCPU/<locked-basename>`，不得重复；物理 target/support 不得是 symlink。
5. official chiplab tree、tool links、support header/license、doctor、evaluator、manifest 和 golden allowlist 继续使用 baseline 哈希链。
6. overlay/smoke verifier 重新从 Git 读取 base/spec/replacement blob，并同时核对 report、marker、物理文件的 SHA256/size；仅让 manifest 与物理文件一起自洽不构成通过。
7. replacement source commit、spec commit 或当前 HEAD 改变后，旧 overlay 必须拒绝。
8. smoke 在构建和仿真结束后再次核对 DUT exact union、Git blob provenance、marker 与 overlay report；post-run 复验失败时不得生成可消费的结果报告。

## Claim 与状态

mixed overlay 固定输出：

```text
mode=diagnostic
provenance_mode=mixed_candidate
gate_kind=component_replacement
base_candidate_locked=true
candidate_locked=false
gate_eligible=false
```

即使 diagnostic smoke 功能通过，也只能证明该 composite DUT 在所执行用例上的行为，不得提升 `team_golden_candidate`、不得满足 locked baseline gate。更新正式 reference 必须另开 manifest/ADR PR，经人工确认并跑完整影响门禁。

没有 replacement 参数时，原 locked baseline export/overlay schema 与语义保持兼容；回归必须证明默认路径仍只消费 `a158aa8`。

## 最低测试

- 正向：parser/source binding；等字节单文件 replacement；locked baseline 默认路径回归。
- 负向：dirty worktree、参数组合错误、spec/source path traversal、symlink mode、非 allowlist target、duplicate/missing entry、header/宏 include、missing Git blob、base/replacement hash mismatch、额外顶层/嵌套 HDL、stale spec/source commit、mixed gate-eligible 伪装。
- 集成：从 clean committed HEAD 建 diagnostic overlay，执行官方 smoke control；报告保持 diagnostic，无论功能结果如何均不得出现 gate-eligible PASS。
