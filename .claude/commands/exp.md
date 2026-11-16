---
description: 新建一个实验的脚手架
argument-hint: <实验名> <模型名> <数据集>
---
为实验 $ARGUMENTS 创建：configs/ 下的配置文件、experiments/ 下的一键运行脚本（接受 seed 参数）、results/ 下的目标路径约定，并把 5 个 seed 的命令追加到 experiments/queue.txt（先不执行）。
运行脚本必须经 common/run.py 记录，测试集评估必须调用 eval/ 的统一入口。完成后列出新文件与队列中新增的命令，等我确认再启动队列。
