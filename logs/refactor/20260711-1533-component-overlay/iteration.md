# 20260711-1533-component-overlay

- 状态：`draft`
- 分支：`refactor/20260711-1533-component-overlay`
- Base：`fec3e1460fb9658329d5221e062c116090ef4d99`
- 日志更新时 HEAD：`322a9e01da06b95b041059cad7c82cdafa881e35`（待形成新的 source commit）
- Owner / Agent：Codex
- 目标边界：`component_replacement_overlay`

## 选择理由

baseline 迭代证明当前 locked `a158aa8` 在 `func_lab19` 失败。准备修复 cacop 时又确认当前开发线没有历史 `rtl/icache.v`、`rtl/dcache.v`，现有 `chiplab-overlay` 只能从单一历史 commit 整体导出 22 个文件，不能把一个已提交的新实现安全替换进 locked golden 集合。

因此本轮唯一目标是补齐后续所有最小替换共同依赖的 harness：固定 `a158aa8` 作为 base，只允许通过结构化、已提交、可哈希的 manifest 一对一替换 locked component，并强制 mixed overlay 为 diagnostic。此迭代不修改 CPU 行为，不宣称修复 cacop。

## 初始事实

- 分支最初以 `refactor/20260711-1533-cacop-recovery` 从 `fec3e14` 创建；发现 harness 缺口且尚无改动/提交后，重命名为当前 prerequisite 分支。
- `main` 与 `origin/main` 保持 `20cae5fd66391f4a1bccc1b87035be421039144b`。
- 当前工作树干净。
- `git diff a158aa8 -- rtl/icache.v rtl/dcache.v` 显示两个历史文件在当前开发线均不存在；不能直接构造完整 22-file diagnostic candidate。
- baseline PR 因 GitHub 443 超时仍为本地 `awaiting_push`；本分支锁定其本地 commit 为 base，并保持 Draft，不自动合并。

## 行为合同

已写入 `docs/contracts/component-overlay.md`。实现固定 locked base、clean source HEAD、严格 JSON spec、普通 Git blob、22-file exact union、header/license/source hash、双 root iteration lock 与 post-run DUT 复验。mixed 输出固定为 diagnostic，不能满足 locked baseline gate。

## 尝试与失败

- 直接进入 cacop 修复被停止：当前开发线不存在历史 cache RTL，现有 evaluator 没有逐组件 replacement 输入；继续编码会导致不可执行或不可追溯的 DUT。
- 本轮不会用修改 `reference/manifest.lock`、复制完整旧 RTL 或放宽 `candidate_locked` 作为捷径。
- 第一轮单测为 `57/59 PASS`：旧 overlay fixture 缺少新 `path` 字段；补齐 schema 后恢复通过。
- 独立只读审核发现并修复：嵌套 RTL/同名错位路径、diagnostic provenance 绕过、report projection、重复 JSON key/布尔 schema、空 doctor checks、doctor 解析/哈希竞态、不同 OUT_DIR 共享 worktree 并发 reset、post-run DUT 漂移及 Verilog 外部文件/DPI 依赖。
- 旧 `322a9e0` exact evidence 经复核后发现比较器仍可能接受空/空哈希证据、未复算物理 artifact/raw log，并存在 warning tuple key collision；该 evidence 已明确作废，不用于最终 claim。
- 加固过程中真实触发并修复：固定 `.tmp` symlink 风险、父目录替换 TOCTOU、目录 fsync 失败后残留 PASS、旧锁持有者删除新锁、半写锁、比较输出在取得锁前被并发删除、post-smoke 错用 pristine workspace 指纹，以及 release 后撤销 report 会删除后继输出的竞态。最终采用锁内 publication marker；裸 report 不再算证据，释放后不再按路径撤销。
- post-smoke 合同现在只排除九个固定生成路径和 `.rtl-smoke.lock` 控制文件。把遗漏的 `config.log` 加入后，对旧真实 locked/mixed worktree 与只读 reference 的复算均为同一 `1535` entries、SHA256 `a089db6e8f4fc1cffdfc46d4f76b1233b1004c127a87b03a3feac0ca35eb26b8`；这只验证过滤边界，不恢复旧 evidence 的有效性。
- 最终开发态检查发现 131 项 Windows 自动化测试，其中 123 项通过、8 项因平台/权限条件跳过；WSL 实际执行 `test_refactor 77/77 PASS` 与 identity comparator `24/24 PASS`，没有 skip。WSL symlink、parent-swap、directory-fsync、lock replacement 场景均实际执行；Windows 路径覆盖祖先目录 handle 与 lock handle 删除。Python compile、`flake8 --select=F` 和 `git diff --check` 通过。
- 新增负测证明：物理 `compile.log` 隐藏 error、两侧共同伪造 warning PASS、共同加入 oracle bypass 字段、缺失/篡改 publication marker、部分获取锁后的回滚释放失败和 `KeyboardInterrupt` 都会失败。模拟“锁已实际释放后再抛错”时，命令返回错误且不输出 PASS，但不再竞态删除已经 marker-bound 的报告。
- Claude bridge 两次均在模型启动前失败：第一次 backend 不允许 reviewer tools，第二次缺少 `GEEKPIE_CLAUDE_API_KEY`。原始终态已保存，不能称为 Claude 审核；独立 Codex 复审仅作为降级检查。
- 以上仍不是 clean committed HEAD 的最终 evidence；正式 gate 在 `summary.json` 中保持 pending。

## 当前门禁

实现和跨主机开发态单测已完成，真实 locked/mixed chiplab overlay、Scala、官方 smoke、独立 rtl-static/Yosys 尚未在新的 clean source commit 上执行；Claude claim review 为 `unavailable`。所有正式门禁仍保持 pending，不能形成 PASS claim。

## 回退

通过 revert 本迭代 Draft PR 回退。locked baseline 路径必须保持字节级兼容；任何 replacement 功能都只能是显式 opt-in diagnostic。

## 下一步

形成并立即推送 source commit 后，在 clean HEAD 上运行 doctor、自动化测试、Scala、locked candidate overlay 与等字节 ALU mixed overlay；随后执行官方 diagnostic smoke、最新 experiment-audit/claim review 和证据提交。证据齐全前不武断创建 PR，任何 PR 仍只能是 Draft，代理不合并 `main`。
