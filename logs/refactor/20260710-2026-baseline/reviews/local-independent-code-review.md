# 本地独立代码审查

> 历史审查快照：本文件保留当时发现与失败，不代表 `45043bd` final evidence 的活动结论。最终判定见 `baseline-hardening-rereview.md` 与 `experiment-audit.md`。

- 审查类型：本地独立只读代码审查
- 审查者：Codex 子代理 `automation_code_review`
- 审查日期：2026-07-10
- 审查对象：当前未提交工作树中的 `tools/refactor.py`、`Makefile`、`tests/test_refactor.py`、`reference/*.lock`、`spinal/build.sbt`，以及 WSL `/tmp/nscscc-{final,d22,d76}-evidence`
- 身份声明：**本文件不是 Claude 审核，不能替代 `claude-review` gate。**
- 总体结论：`blocking`。当前迭代保持 Draft/blocked 是正确的；在下列阻塞问题修复前，自动化不能作为 baseline PASS、golden 晋升或迭代 ready 的可信门禁。

## 已核实的本次运行事实

1. `artifacts.json` 中三份 smoke report 和 locked overlay manifest 的 SHA-256 与 WSL 文件一致。
2. locked run 确实使用 `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`，报告为 `candidate_locked=true`；原始日志在 PC `0x1c07c79c` 出现 `t0(r12)` DiffTest mismatch，执行 `172552` 条指令、`602903` 周期。
3. `d22c13c` 诊断 run 为 `candidate_locked=false`，原始日志包含 `END by Syscall` 和 `Reached test end PC.`，功能 parser 为 PASS；`d76ca40` 在同一 PC 出现同类 mismatch。三次日志的 bus-delay seed 都是 `5570815`。
4. 审查时重新核对 locked work 中 22 个 DUT 文件，均仍匹配 overlay manifest；已安装 NEMU 文件也仍匹配 lock 中 SHA-256。这里只说明当前磁盘没有观察到篡改，不能弥补自动化没有在运行时强制复验的问题。
5. 三份报告的总状态均为 FAIL：locked 和 d76 同时功能失败/静态失败；d22 功能通过但静态失败。报告分别记录 locked 的 280 条 DUT、364 条官方环境 Verilator warning，以及 d22/d76 的 195/364 条 warning。

## Blocking findings

### B1. `validate-iteration` 可让伪造或失败迭代通过

`tools/refactor.py:863-912` 只检查文件存在、JSON 可解析和 gate 数字非负；不检查 status 枚举、required gate、`executed == passed + failed`、`skipped == 0`、失败 gate、head SHA、命令字段或 artifact SHA。`tools/refactor.py:893-900` 对 ready/complete 只读取两个可手写的 Claude summary 字段，甚至不绑定 reviewed head/raw response。空 `gates`、空 `commands.jsonl` 或带失败 gate 的 ready 迭代都可能返回 0。

修复建议：为 iteration、gate、command、artifact 和 review 建立严格 JSON Schema；按 change-impact matrix 计算 required gates；校验计数恒等式、零 skip/fail、base/head/current HEAD、review target SHA、raw review SHA 和所有本地 artifact SHA。为每种伪造反例增加负向测试。

### B2. smoke 未把实际运行 DUT 绑定到 overlay 证据

overlay 报告固定写到 `tools/refactor.py:662-676`；`tools/refactor.py:754-765` 只读取固定报告和工作目录内可修改的 marker，并且仅核对 chiplab commit。它没有比较报告与 marker 的 SHA、iteration id、DUT/support 文件哈希、额外 RTL、submodule 状态或工具链接。`tools/refactor.py:816-820` 随后直接沿用这些元数据。因此 overlay 后修改 RTL、复用旧报告或用不同 iteration 参数运行，都可被错误标成原 candidate。

修复建议：每次运行使用不可复用的 run id 和独立 report 路径；smoke 前要求 argument/report/marker iteration 一致，重算全部 overlay/support 文件和额外源文件集合，复验 chiplab/submodule 状态，并把 overlay report SHA 写入 smoke report。开始新 run 时先原子失效旧 PASS。

### B3. `candidate_locked=false` 仍可形成正式 PASS

`tools/refactor.py:445-494` 接受 candidate override，但 `golden-export` 仍写 `status=pass`；`tools/refactor.py:535-536,665-678` 的 overlay 同样无条件 PASS；`tools/refactor.py:818-826` 只展示 `candidate_locked` 而不把 false 作为 gate 失败。只要一个非锁定提交功能和 warning 都通过，现有正式 smoke report 就会 PASS。

修复建议：正式 baseline 命令完全禁止 override，并强制 `dut_source=candidate`、完整 commit 等于 lock、`candidate_locked=true`。另设 `diagnostic-overlay`/`diagnostic-smoke`，其结果只能是 diagnostic，不能被 status/claim/PR gate 消费。

### B4. 工具链和 NEMU oracle 没有绑定到 smoke

`tools/refactor.py:383-410` 只校验下载包 SHA；已安装 NEMU/picolibc/QEMU 只检查文件存在，GCC/SBT/Verilator/Yosys/JDK 主要靠可伪造的版本子串。`tools/refactor.py:582-584` overlay 也只检查工具目录存在；`tools/refactor.py:739-767` 的 smoke 不要求 fresh doctor PASS，报告不记录 tool root、NEMU/编译器/Verilator 文件哈希或 doctor report SHA。保留下载包并替换已安装 NEMU，即可让 doctor 与 smoke 使用不同 oracle。

修复建议：锁定并复验安装产物 manifest，至少直接校验 NEMU `.so`；记录 GCC、picolibc、QEMU、SBT、Verilator、Yosys、JDK 的可执行文件/关键目录哈希。smoke 必须消费同一 iteration、同一 manifest SHA、限定时效的 doctor PASS，并在结果中绑定 doctor SHA。

### B5. 无效 case 可以运行旧的 `func_lab19`，却按请求 case 报告 PASS

`tools/refactor.py:773-782` 只信任 `configure.sh` 退出码，`tools/refactor.py:796,821` 又用用户输入构造 artifact 路径和报告 case。锁定 chiplab 的 `configure.sh:480-482` 对 unavailable software 使用无参数 `exit`，返回 0，并在写新 `config-software.mak` 前退出；仓库默认配置仍是 `RUN_SOFTWARE=func/func_lab19`。因此无效 `--case` 会继续编译/运行旧 case，成功时却声明请求 case 通过。

修复建议：从锁定 commit 的脚本/配置发现合法 case，拒绝其他输入；configure 后解析 `config-software.mak`，要求实际 `RUN_SOFTWARE` 与请求值逐字一致；把 `Software ... unavailable`、usage 和未生成新配置视为失败，并验证配置文件 mtime/run id。

### B6. 未执行的 rtl-static 会被记为 PASS，计数也自相矛盾

`tools/refactor.py:784-793` 在 `compile.log` 不存在时令 `warnings=[]`、`warnings_ok=true`；`tools/refactor.py:815,833-837` 因而输出 `rtl_static_status=pass, executed=0, passed=1`。configure/build 提前失败时，functional 也会出现 `executed=0, failed=1, skipped=0`。旧 compile log 未在 run 前清理，失败重跑还可能消费 stale log。

修复建议：使用显式 `not_run/pass/fail` 状态机；只有本次 build 命令已执行且返回 0、compile log 在 run 开始后新生成并绑定哈希时才能 static PASS。所有层级强制 `executed=passed+failed`，未运行计入 skipped 并使 required gate 总体失败。

### B7. 当前 `commands.jsonl` 不是实际可复现命令

`logs/refactor/20260710-2026-baseline/commands.jsonl:7` 的 overlay 记录缺少 CLI 强制的 `--iteration-id` 和 `--chiplab-ref`；第 8 行 smoke 缺少强制的 `--iteration-id`；第 9-12 行声称执行 `rtl-smoke --candidate-commit`，但该参数只属于 overlay，`tools/refactor.py:947-955` 的 smoke parser 不接受它。审查中直接复现该参数组合会 argparse exit 2，不可能得到日志所写的 exit 1 和约 68 秒耗时。

修复建议：命令记录必须由 `run_command` 自动写入，不允许手工摘要代替原命令。诊断 run 分别记录完整的 overlay override 命令和无 override 的 smoke 命令，并保存 cwd、环境白名单、stdout/stderr artifact、exit code 和 report SHA。

## Major findings

### M1. timeout 没有终止进程树

`tools/refactor.py:137-179` 使用 `subprocess.run(timeout=...)`，超时时只保证直接子进程被杀；`make` 启动的 Verilator/simulator 子进程可能继续写同一工作目录，污染下一次 run。

修复建议：POSIX 下使用新 session/process group，超时时先 TERM 后 KILL 整个组；Windows 使用 job object。等待进程树退出后再封存日志，并以 run lock 阻止同目录并发。

### M2. 功能 parser 没有核对 UART/result artifact，warning policy 也漏掉 build stderr

`tools/refactor.py:696-736` 只解析 simulator stdout/stderr；`tools/refactor.py:795-807` 仅给 UART/trace 计算哈希，不判断内容或测试身份。`tools/refactor.py:784-786` 只从 Verilator `compile.log` 收集 `%Warning`，而本次 `02-build.log` 中的 C++ compiler warning 不在统计内。当前 d22 的正向 marker 足以支持“该 parser 通过”，但不能泛化为 AGENTS.md 所定义的 UART、DiffTest、result-file 三重闭环。

修复建议：为每类 case 定义官方 result/UART parser 和期望；报告保存实际软件镜像 SHA、seed 和首个 mismatch。分别命名 Verilator RTL warning gate 与 host build warning gate，或解析完整本次 build 输出。

### M3. Make/Scala gate 使用的工具与合同不一致

`Makefile:26-27` 没有把 `CHIPLAB_TOOL_ROOT` 传给 smoke，可能让 overlay 与执行使用不同工具根。`Makefile:14-15` 的 `scala-check` 只是 PATH 中的 `sbt test`，没有 format、warning policy、锁定 launcher、结构化报告或测试存在性检查；当前工程确实没有 Scala test source。`spinal/build.sbt:7-12` 的 IDSL plugin 配置本身正确，但不足以兑现完整 `scala-check` 合同。

修复建议：所有入口显式传同一 tool root/context；通过锁定 SBT/JDK wrapper 执行 format、compile、test，并将零测试按当前 gate 合同记为 skip/fail或拆成单独 compile gate。

### M4. 启动命令不存在时不会生成结构化失败

`tools/refactor.py:137-179` 不捕获 `FileNotFoundError/OSError`，`tools/refactor.py:963-970` 又只捕获 `RefactorError`。缺少 Verilator、Yosys、git、stat 等工具时会 traceback，doctor report 可能根本不存在。

修复建议：把进程启动失败规范化成 exit 127/126 的 `CommandResult`，继续写 status=fail 的报告；补 missing executable 和 permission denied 测试。host 检查还应约束锁定 Linux/架构，而不只是 `os.name == posix`。

### M5. 生成目录 marker 与扁平导出保护不足

`tools/refactor.py:427-442` 只凭同名 marker 存在就递归删除，不校验 purpose、规范化目标、创建 run 或 owner；用户还可把 `OUT_DIR` 指到源码树。`tools/refactor.py:120-134` 只拒绝完整路径重复，但 `tools/refactor.py:455` 按 basename 扁平导出，未来两个同名源文件会静默覆盖。

修复建议：限制为专用 generated root；marker 绑定绝对路径、purpose、run id 和随机 token，删除前全部匹配；拒绝 tracked/reference/logs 目录。保持相对目录结构或显式拒绝重复 basename。

## 测试缺口

`tests/test_refactor.py:27-63` 覆盖基本 log marker，`tests/test_refactor.py:65-86` 覆盖最简单的 marker 删除边界，但没有覆盖 invalid case、候选锁、运行时 DUT 篡改、stale/missing compile log、命令不存在、timeout 进程树、计数不变量、伪造 ready/review 或工具 oracle 替换。这些负向测试应在自动化 PR ready 前补齐。

## 建议修复顺序

1. 先修 B1、B5、B6，消除直接假 PASS 和错误计数。
2. 引入统一、不可变的 run context，联合修复 B2、B3、B4、B7。
3. 补齐上述负向测试，再处理 timeout、UART/result parser 和跨平台失败报告。
4. 修复后重新生成三组 evidence；旧证据可保留为问题定位材料，但不能作为新自动化 gate 的自证结果。
