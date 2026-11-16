# E2-b Memory 进产物目录

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：工程线
- 估时：0.5 天
- 依赖：S4a-b、E2

## 提示词

扩展 make artifacts：可选加入 user_memory.jsonl、memory_emb.npy、item_meta.json（标题、类目、details；price 缺失时为 null 并能被下游正确处理）。
原型的“用户画像”接口改为读取 user_memory.jsonl；没有 Memory 的用户返回明确的空状态，不报错。
导出一个中间版本 v1m 用于联调（不对外宣称，manifest 写明）。

## 产出
artifacts/v1m/；serving 画像接口

## 验收
对有/无 Memory 的两个用户，画像接口分别返回内容与空状态

## 论文落点
第 5 章数据设计：产物清单
