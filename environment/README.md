# environment/ — 环境锁定

- **用途**：记录各实验环境的依赖锁定文件，保证复现一致。
- **输入**：conda / pip / uv 的实际安装结果。
- **产出**：`research.yml`（CPU 侧：评估、数据画像、表格管线）、`recbole.yml`（RecBole 基线训练）；版本号同时记入 `docs/decisions.md`。
- **用法**：`conda env create -f environment/research.yml`，之后 `make check-env PY=$(conda run -n research which python)` 确认依赖齐全。