# common/ — 运行记录

- **用途**：实验运行的公共记录模块，确保每次训练/评估有统一的元数据。
- **输入**：实验名、模型名、seed、配置文件。
- **产出**：`results/{exp}/{model}/seed{n}/` 下的 `config.yaml`、`train_log.csv`、`manifest.json`。

## run.py

`start_run(exp, model, seed, config)` 上下文管理器，退出时写 `manifest.json`。

- **dirty 判定**：已跟踪文件的任何改动、以及产物目录（`results/`、`build/`、
  `artifacts/`、`figures/`、`thesis/generated/`）之外的未跟踪源码文件，都算 dirty。
  dirty 时目录前缀改 `_dirty_{exp}` 并打印警告，结果不会被 `make_tables` 采集。
- **manifest 字段**：git commit、dirty 状态与改动文件清单、HEAD 上全部 tag、
  完整命令、起止时间（带时区）、GPU 型号与峰值显存、每轮耗时、best_epoch、
  stop_reason（patience / max_epoch / failed / completed）、data_scope。
- **异常路径**：训练抛异常时也落 manifest，`stop_reason=failed`，并记录异常信息。