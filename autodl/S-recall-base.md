# AutoDL 操作步骤（S-recall-base 召回基线）

本机 recbole_env 是 CPU 版，25 个 run（5 模型 × 5 seed，约 20 小时）必须在 AutoDL 的 `rec` 环境跑。

## 为什么本机 CPU 冒烟仍然值得跑

RecBole 的训练分两段：

| 段 | 在哪算 | CPU 冒烟能否验证 |
|---|---|---|
| 训练（前向/反向 200 epoch） | GPU 才能跑得快 | 只能验证代码路径通不通，**不出性能数字** |
| 打分 → per_user → Recall/NDCG | **全程 CPU** | ✅ 完全等价：指标只取决于模型权重，与算力无关 |

所以本机冒烟验证的是**正确性**（冻结切分加载、ID 映射、屏蔽口径、落盘格式），
不产出任何性能数字。2026-11-27 的 BPR 2-epoch 冒烟就是这样抓出 3 个 bug 的
（`Interaction` 取列方式、batch 是四元组、`manifest` extra 被覆盖）——这些 bug 若留到
AutoDL 上，会各浪费一轮 20 小时队列。

**唯一必须在 GPU 上确认的**：单 epoch 耗时、峰值显存、SimGCL 在 RecBole-GNN 下能否加载。

## 0. 前置

```bash
cd /root/autodl-tmp && cd deeptime-rec
git pull                                # 必须是干净工作区，否则结果会带 _dirty_ 前缀
git status --porcelain                  # 应无输出
conda activate rec
```

## 1. 装 RecBole-GNN（SimGCL 需要）

```bash
git clone https://github.com/RUCAIBox/RecBole-GNN.git /root/autodl-tmp/RecBole-GNN
SITE=$(python -c 'import site;print(site.getsitepackages()[0])')
cp -r /root/autodl-tmp/RecBole-GNN/recbole_gnn "$SITE"/
python -c "import recbole_gnn; from recbole.utils import get_model; get_model('SimGCL'); print('SimGCL OK')"
```

## 2. 先 smoke（RTX 4090 上约 3 分钟）

```bash
python experiments/run_recall_baseline.py --model bprmf --seed 0 --epochs 3 \
    --results-dir results/_smoke/recall
cat results/_smoke/recall/ch3_recall/baselines/bprmf/seed0/metrics.json
```

确认指标非零、`manifest.json` 里 `git_dirty=false`、`device` 是 cuda。

## 3. 正式队列

```bash
bash experiments/queue.sh                 # tmux 会话 exp 后台执行 26 条
tmux attach -t exp                        # 查看
tail -f experiments/queue.log             # 日志
bash experiments/queue.sh --status        # 进度
```

## 4. 产物检查

```bash
ls results/ch3_recall/baselines/*/seed*/metrics.json | wc -l    # 应为 25
cat results/ch3_recall/baselines/summary.csv
git add results/ch3_recall/baselines && git commit -m "S-recall-base: 5 基线 × 5 seed"
git push
```

## 注意

- `per_user.parquet` 每个约 650 KB，25 个约 16 MB，`.gitignore` 已放行 results/ 下的 parquet，会入库。
- checkpoint（`*.pth`）被 .gitignore 忽略，不入库；需要复现时重跑训练。
- 结果目录落 `results/ch3_recall/baselines/{model}/seed{n}/`，`make_tables` 会自动采成
  `recall.baselines.{model}.{metric}.mean|std|seeds`。