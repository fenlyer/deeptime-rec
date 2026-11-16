# E0-b 原型代码迁入 serving/

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：工程线
- 估时：0.5–1 天
- 依赖：E0-a

## 提示词

把原型后端代码迁入 serving/（保留原仓库的 commit 号写在 serving/README.md），把 ID 映射改为读取 data/processed/IS/ 的统一映射文件。
本卡只要求旧原型在新位置能启动并返回结果，不改推荐逻辑、不换模型。
serving/README.md 写清启动命令、依赖、环境变量；依赖用 uv 锁定。

## 产出
serving/；serving/README.md

## 验收
按 README 启动后，对一个测试用户能返回推荐列表

## 论文落点
无（为 E1 做准备）
