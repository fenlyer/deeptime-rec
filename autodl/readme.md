
## S1-b 冒烟测试 AutoDL 具体步骤：

  # 1. 在 AutoDL 上 clone/pull 仓库
  cd /root/autodl-tmp
  git clone https://github.com/fenlyer/deeptime-rec.git
  cd deeptime-rec

  # 2. 激活 conda 环境
  conda activate rec

  # 3. 验证数据文件
  ls data/recbole/IS/
  # 应看到 IS.train.inter, IS.val.inter, IS.test.inter

  # 4. 运行 LightGCN smoke 训练（GPU，50 epoch）
  python experiments/recbole_smoke.py --epochs 50
  # 训练约 5-10 分钟，评估约 5 分钟

  # 5. 运行交叉校验
  python eval/crosscheck_recbole.py \
      --checkpoint $(ls -t results/_smoke/recbole/LightGCN-*.pth | head -1) \
      --data-path data/recbole \
      --output results/_smoke/crosscheck.json

  # 6. 或用 queue.sh 一键执行（已加入队列）
  bash experiments/queue.sh --foreground

  预期结果：
  - results/_smoke/recbole/recbole_metrics.json — RecBole 评估指标
  - results/_smoke/crosscheck.json — 交叉校验结果
  - tests/test_verify_recbole_adapter.py 对账 2-4 通过