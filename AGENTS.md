在当前仓库里开一个dev分支，按照以下流程在dev分支中进行开发。你的目的是用一切手段，在合规（jsfa.pdf）的范围内优化cpu，在保证功能测试满分的同时，保证尽可能小的程序执行时间。
1.阅读已有log，聊天记录，文档，综合网络经验与深入思考分析，确定下一轮次改进方案。
2.应用你的改进方案。
3.使用vivado进行综合，进行功能测试。
4.如果vivado综合失败或功能测试未满分，规划修复方案，回到3.
5.提交NSCSCC FPGA Remote Evaluation  skill 进行三次真实烧录测试，取最低一次结果作为当前性能改进决定性。
6.如果真实烧录测试未能带来性能改进，分析结果，选择直接放弃回退当前轮次的修改还是回到1.继续迭代当前轮次。写作log记录这一次改进尝试。
7.审核当前改进是否遵循比赛规则，保证当前改进不引入任何非自动生成的verilog代码。
8.如果NSCSCC FPGA Remote Evaluation 带来相对于上一轮commit（相对于baseline）2x的加速比提升，写作commit message并进行一次commit。如果带来改进但不超过5x，采纳当前改进，视为一轮修改但不commit。
9.每10轮改进，强制进行一轮复杂性审核，深入审核当前代码的复杂性与可读性，在不显著降低性能的前提下大幅简化代码，提升可读性，添加中文注释。这一轮改进也需要沿用1-7的流程，但不需要性能明显改进，只要不退化就能commit。

##重要信息
vivado 地址：D:\Xilinx\Vivado\2023.2
比赛相关文档：https://chiplab.readthedocs.io/zh-cn/latest/Quick-Start.html https://bookdown.org/loongson/_book3/chapter-cpu-chip-design-process.html
聊天记录接口及文档：http://127.0.0.1:8765/api/ai/context；http://127.0.0.1:8765/docs
baseline数据:baseline.txt
这是竞争性的比赛。永远尝试实现超常规的，工业级的改进，与天马行空的想法。
优先在wsl中开发以减少powershell中的报错，提升git效率。
保持持续工作，在达成100x加速前不要停止工作，也不要结束对话，在这之前都不要停下来。
