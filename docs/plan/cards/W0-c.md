# W0-c 数据盘与后台任务队列

- 周次：W0 启动日（11/15 周日（最迟 11/16 上午完成））
- 线：事务
- 估时：1 小时

## 提示词

在 AutoDL 实例上：
1. 确认数据盘路径（如 /root/autodl-tmp），把 processed/、artifacts/ 和体积大的结果文件放在数据盘，仓库内用软链接；把实际路径写进 CLAUDE.md 的”环境”一节。
2. ~~写 scripts/backup.sh~~ → 简化为 git 追踪（.gitignore 放行 `artifacts/*/manifest.json`），不再需要独立备份脚本。
3. 写 experiments/queue.sh：逐行读取 experiments/queue.txt 中的命令，在 tmux 会话 exp 中顺序执行，每条结束后向 experiments/queue.log 追加开始时间、结束时间、退出码；已执行过的行加前缀 # done 。

## 产出
experiments/queue.sh；.gitignore 放行 `artifacts/*/manifest.json`

## 验收
- ~~make backup 成功一次~~ → 不需要（git 管理）
- AutoDL 实例上：数据盘软链接到位，queue.sh 能读取 queue.txt 并执行

## 论文落点
无
