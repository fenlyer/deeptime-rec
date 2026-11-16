# common/ — 运行记录

- **用途**：实验运行的公共记录模块，确保每次训练/评估有统一的元数据。
- **输入**：实验名、模型名、seed、配置文件。
- **产出**：`results/{exp}/{model}/seed{n}/` 下的 `manifest.json`、`metrics.json`、`train_log.csv`。
