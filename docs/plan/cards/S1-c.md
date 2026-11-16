# S1-c 运行记录、配对检验、分层守恒

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S1-a

## 提示词

1. common/run.py：start_run(exp, model, seed, config) 创建 results/{exp}/{model}/seed{n}/；结束时写 manifest.json：git commit、工作区是否有未提交改动、data tag、完整命令、开始与结束时间、GPU 型号、峰值显存、每轮耗时列表、best_epoch、停止原因（耐心耗尽/最大轮数）。工作区不干净时打印醒目警告，并把结果目录前缀改为 _dirty_。
2. eval/paired_test.py：输入两个模型的结果目录（多个 seed），先对每个用户在各 seed 上取平均，再做配对 t 检验与 Wilcoxon 符号秩检验；输出 n、均值差、t、p、d_z = t/√n、Wilcoxon p，写成 JSON。
3. eval/strata.py：按训练集交互数分 3–4 / 5–9 / 10–29 / ≥30 四层，输出各层指标与人数；断言按人数加权的均值与整体指标之差 < 1e-9。
每个脚本配 pytest（paired_test 用构造数据验证 d_z 公式）。

## 产出
common/run.py；eval/paired_test.py；eval/strata.py；对应测试

## 验收
pytest 全过；对一个 smoke 结果目录能生成 manifest.json

## 论文落点
显著性检验方法（以用户为单位，替代 V8 5.5.3 的 t(4) 检验）；冷启动分层口径
