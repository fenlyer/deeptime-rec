# S0-a 校验冻结数据并打 tag

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天

## 提示词

LOO 不变量校验由 data/prepare_data.py 的 verify_loo() 在预处理时写入 processed/{DS}/stats.json 的 split_check 字段（test 每用户恰好 1 对、test/val 不泄漏进 train）。本卡只读取该字段核对，再运行 data/ 下三个 verify_*.py，全部输出保存到 results/verify/。
任何一项失败就停下，报告失败内容，不要修改数据或脚本去“让它通过”。
全部通过后：
1. 为 data/processed/{IS,TH,OP,AJ}/ 下每个文件计算 sha256，写入 data/CHECKSUMS.sha256 并提交；
2. 打 git tag data-v1；
3. 在 docs/decisions.md 记一条：日期、tag、四个数据集的用户数/物品数/交互数（从 stats.json 读，不手填）。

## 产出
results/verify/；data/CHECKSUMS.sha256；tag data-v1

## 验收
sha256sum -c data/CHECKSUMS.sha256 全部 OK；git tag 中有 data-v1

## 论文落点
第 3 章数据集小节的预处理与切分说明
