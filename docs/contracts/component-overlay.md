# Component replacement overlay 行为合同

> 状态说明：该合同保留用于历史的、已提交 Git blob 形式的 leaf replacement。
> 当前 OoO `mycpu_top.v` 是完全可再生且受 Git 跟踪的发布镜像，可满足下文规则 4。
> 当前顶层必须先运行 `make generate-core`、`make publish-check`，并将生成镜像与
> Scala 源码、replacement spec 一起提交；不要为迁就未提交生成物而放宽 overlay 的
> Git provenance 校验。

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
4. spec 与 replacement source 必须都是该 source HEAD 中的普通 Git blob；不读取或回退到未提交工作树内容。staged、untracked、文件模式以及忽略且仅忽略行尾 CR 后仍存在的 diff 均失败；行尾空格不是可忽略差异。Windows/WSL 对同一 checkout 的纯 CRLF 物化差异允许通过，但 manifest 必须分别记录真实 `worktree_porcelain_clean`、`worktree_semantic_clean`、原始 status 条目数和 `worktree_eol_normalization_only`，且 replacement payload 仍只读取已提交 Git blob。
5. 任一失败在开始时删除同 iteration 的旧 overlay report，不能留下可复用的旧 diagnostic/PASS。
6. overlay 与 smoke 必须使用同一 Linux `CHIPLAB_WORK_ROOT`。两者同时获取 `OUT_DIR` 和 work root 下的 iteration lock；任一活动命令存在时，另一命令不得 reset 或消费同一 DUT。锁持有者保留打开的文件描述符，释放时必须核对 inode/file identity、iteration、operation 与 run id；旧持有者不得删除后来者的锁，半写锁只能由原持有者清理。正常 producer/consumer 都必须遵守这些协作锁；同用户恶意进程绕过锁实施路径替换不属于本合同保证的威胁模型。
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
  REPLACEMENT_SPEC=reference/component-replacements/core-top.json \
  SOURCE_HEAD="$SOURCE_HEAD"

make rtl-smoke \
  OUT_DIR=/tmp/nscscc-component-overlay \
  CHIPLAB_WORK_ROOT=/tmp/nscscc-component-work \
  ITERATION_ID="$ITERATION_ID" \
  DIAGNOSTIC=1
```

doctor、overlay、smoke 必须共用 `OUT_DIR`；doctor 与 overlay 必须共用 `CHIPLAB_REFERENCE`；overlay 与 smoke 必须共用 `CHIPLAB_WORK_ROOT` 和 `ITERATION_ID`。`DIAGNOSTIC` 只接受空、`0` 或 `1`。spec、replacement 和 evaluator 必须已提交，并满足规则 4 的 semantic-clean/CRLF-only 合同，再运行 doctor/overlay/smoke。

若进程被 `SIGKILL` 或机器断电，fail-closed lock 文件可能保留。只能在人工核对记录的 PID 已不存在且没有 overlay/smoke 进程后删除对应 `.locks/iterations/<iteration-id>.lock`；同时删除该未完成命令对应的 `*.publication.json`，不得由脚本按时间自动清锁。

## Spec schema

```json
{
  "schema_version": 1,
  "replacements": [
    {
      "target": "rtl/mycpu_top.v",
      "source": "rtl/mycpu_top.v",
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
- replacement 禁止本地 `` `define/`undef``、token-paste、历史 base 未引用的新宏、`$readmemh/$readmemb`、文件 I/O、dump/random、plusargs、`$system` 和 DPI 等未绑定外部依赖。所有可写 simulator log 或改变仿真终止状态的 system task 也必须拒绝，包括 `$display/$write/$monitor/$strobe` 及其文件/进制 variants，以及 `$finish/$stop/$fatal/$error/$warning/$info/$exit`。其他未知 `$identifier` 默认拒绝；只允许代码中明确列出的无外部副作用 elaboration/bit-query function allowlist，例如 `$signed/$unsigned/$clog2/$bits`。扫描忽略注释和字符串。内联 lint 注解默认拒绝；唯一例外是 `rtl/mycpu_top.v` 中由 package gate 生成并严格核对作用域的 41 对 module-scoped `DECLFILENAME` 和 7 对 `UNUSEDSIGNAL` 注解。数量、类别、配对或位置任一漂移都拒绝。未来若活动功能确需其他输入或注解，必须先扩展合同并记录 Git blob、SHA256 和 overlay target。

## 导出与 overlay 不变量

1. 先按 locked allowlist 导出 22 个 base Git blob，再对 spec target 做一对一替换；最终 target 文件数仍精确为 22。
2. 每个文件 entry 标记 `source_kind=golden|replacement`。replacement entry 同时记录 base source/hash、replacement source/hash、spec source/hash。
3. `IP/myCPU` 中允许的 HDL exact union 只包含 22 个目标 basename 与锁定 `mycpu.h`；递归枚举子目录，任何额外 `.v/.sv/.vh/.h` 都失败。
4. manifest 中 overlay path 必须精确为 `IP/myCPU/<locked-basename>`，不得重复；物理 target/support 不得是 symlink。
5. official chiplab tree、tool links、support header/license、doctor、evaluator、manifest 和 golden allowlist 继续使用 baseline 哈希链。
6. overlay/smoke verifier 重新从 Git 读取 base/spec/replacement blob，并同时核对 report、marker、物理文件的 SHA256/size；仅让 manifest 与物理文件一起自洽不构成通过。
7. replacement source commit、spec commit 或当前 HEAD 改变后，旧 overlay 必须拒绝。
8. smoke 在构建和仿真结束后再次核对 DUT exact union、Git blob provenance、marker 与 overlay report；post-run 复验失败时不得生成可消费的结果报告。
9. overlay 同时记录 pristine official workspace 指纹，以及排除固定 smoke 生成路径后的 post-smoke 指纹。后者只排除 `obj_dir`、simulator `output/tmp`、本用例 software obj、compile log、两份 configure 输出与本用例 log 这九个路径及 `.rtl-smoke.lock` 控制文件；其他 tracked/untracked official 文件变化仍失败。不得复用 pristine 指纹直接判断已运行过 smoke 的工作区。
10. 结构化 JSON 通过同目录临时普通文件原子写入。POSIX 使用已验证 directory fd 的相对 open/replace，Windows 在写入期间持有禁止 delete/rename 的目录 handle。producer 在全部协作锁内先删除旧 report/marker，再写 report，最后原子写 `<report>.publication.json`；marker 精确绑定 operation、iteration、run id、report SHA256 和 publisher SHA256。consumer 必须先取得同一组协作锁并通过 marker helper 读取；缺 marker、marker 不匹配或仅有裸 PASS JSON 均不是证据。锁释放失败后不再按路径撤销已发布文件：残留锁会阻止消费；若底层锁已实际全部释放后才报告异常，marker/report 仍保持自洽，但调用命令的非零退出仍必须记录。

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

## Identity control 比较

等字节 replacement 的 control 必须由统一入口生成比较证据：

```bash
make identity-compare \
  OUT_DIR=<shared-output> \
  CHIPLAB_WORK_ROOT=<shared-work-root> \
  CHIPLAB_REFERENCE=<locked-reference> \
  CHIPLAB_TOOL_ROOT=<locked-tool-root> \
  LOCKED_ITERATION_ID=<locked-id> \
  MIXED_ITERATION_ID=<mixed-id>
```

比较器按固定路径读取并哈希 locked/mixed 的 overlay report、overlay manifest 和 `rtl-smoke` report。执行期间按 iteration id 排序，先同时持有两侧 `OUT_DIR` 与 `CHIPLAB_WORK_ROOT` 锁，再清理自己的旧输出；并发命令已有的 comparison report 不得在锁冲突前被删除。部分获取失败时也必须逐把尝试释放所有已取得的锁。它只接受 marker 已发布的 overlay/smoke report，重新运行当前 doctor/source/Git blob/post-smoke workspace 绑定检查，逐个复算 `run_prog` 下九个精确 canonical artifact 和三份 canonical raw log，并从 raw log 重新解析 build error、warning 与仿真结果。环境、单用例 counts、未执行 rtl-static 的固定披露、oracle role 和 result-file policy 也必须匹配官方 wrapper 语义，不能两侧一起伪造后通过。发布前再次核对六份输入 JSON 和当前运行时锚点未变化。输出只能写入 mixed iteration 的 `identity-comparison.json`，不接受任意输出路径；`OUT_DIR`、目标或父目录为 symlink/junction 时失败且不得触碰其指向对象。输入/schema/物理证据错误必须在仍持锁时删除本命令的 report/marker 并返回 2；比较不一致写 `status=fail` 后返回 1；全部一致才返回 0。identity 输出本身也必须有匹配的 publication marker；锁释放异常返回 2，但不在释放后执行有竞态的路径删除。

比较结果固定 `gate_eligible=false`，只允许声明“指定用例的 manifest-bound DUT/测试输入投影与选定观测证据一致”。`Vsimu_top__ALL.a`、simulator `output`、编译/仿真日志、绝对路径、run id、时间戳和耗时不属于 identity claim；这些字段不同不得被隐藏，也不得据此宣称整个构建字节可复现、CPU PASS 或 RTL 形式等价。

## 最低测试

- 正向：parser/source binding；等字节单文件 replacement；locked baseline 默认路径回归。
- 负向：dirty worktree、参数组合错误、spec/source path traversal、symlink mode、非 allowlist target、duplicate/missing entry、header/宏 include、missing Git blob、base/replacement hash mismatch、额外顶层/嵌套 HDL、stale spec/source commit、mixed gate-eligible 伪装。
- 集成：从 clean committed HEAD 建 diagnostic overlay，执行官方 smoke control；报告保持 diagnostic，无论功能结果如何均不得出现 gate-eligible PASS。
