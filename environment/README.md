# environment/ — 环境锁定

- **用途**：记录各实验环境的依赖锁定文件，保证复现一致。
- **输入**：conda / pip / uv 的实际安装结果。
- **产出**：`recbole.yml` 等环境文件，版本号同时记入 `docs/decisions.md`。