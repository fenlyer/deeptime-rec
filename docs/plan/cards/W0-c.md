# W0-c 数据盘、备份与后台任务队列

- 周次：W0 启动日（11/15 周日（最迟 11/16 上午完成））
- 线：事务
- 估时：1 小时

## 提示词

在 AutoDL 实例上：
1. 确认数据盘路径（如 /root/autodl-tmp），把 processed/、artifacts/ 和体积大的结果文件放在数据盘，仓库内用软链接；把实际路径写进 CLAUDE.md 的“环境”一节。
2. 写 scripts/backup.sh：把 results/ 下所有 metrics.json 与 manifest.json、artifacts/*/manifest.json、thesis/、refs/、docs/ 同步到备份位置（我会告诉你是网盘还是本地机器），加进 Makefile 的 backup 目标。
3. 写 experiments/queue.sh：逐行读取 experiments/queue.txt 中的命令，在 tmux 会话 exp 中顺序执行，每条结束后向 experiments/queue.log 追加开始时间、结束时间、退出码；已执行过的行加前缀 # done 。
用两条 echo 测试命令验证队列，然后停下。

## 产出
scripts/backup.sh；experiments/queue.sh；Makefile 的 backup 目标

## 验收
make backup 成功一次；queue.log 中两条测试命令退出码为 0

## 论文落点
无
