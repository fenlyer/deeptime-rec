# Amazon Review 数据集

## 数据集概览

| 数据集 | 简称 | 用途 | 预期大小 |
|--------|------|------|----------|
| Industrial & Scientific | IS | 主实验 | 46.6MB |
| Tools & Hardware | TH | 跨域验证 | 364MB |
| Office Products | OP | 跨域验证 | 238MB |
| Automotive | AJ | 跨域验证 (含多行为) | 227MB |

## 快速开始

```bash
# 一键下载 + 预处理
bash quick_start.sh

# 或分步执行:
python3 download_data.py              # 下载 (支持断点续传)
python3 prepare_data.py --k-core 5    # 预处理
```

## 脚本说明

- **download_data.py** - 下载脚本 (支持断点续传、并行)
- **prepare_data.py** - 预处理脚本 (K-core 过滤、时序划分)
- **quick_start.sh** - 一键执行下载+预处理

## 下载参数

```bash
python3 download_data.py --source snap --workers 4
# --source: 数据源 (snap/deepyeti)
# --workers: 并行数 (默认 4)
# --dry-run: 仅显示下载列表
```

## 预处理参数

```bash
python3 prepare_data.py --categories IS TH --k-core 5 --output-format both
# --categories: 要处理的类别 (IS/TH/OP/AJ)
# --k-core: K-core 过滤阈值 (0=不过滤, 推荐 5)
# --output-format: 输出格式 (csv/parquet/both)
# --stats-only: 仅输出统计信息
```

## 目录结构

```
data/
├── raw/                    # 原始 JSON.gz (下载后)
│   ├── reviews_*.json.gz   # 评论数据
│   └── meta_*.json.gz      # 物品元数据
└── processed/              # 处理后数据
    ├── IS/                 # 各类别子目录
    │   ├── train.csv       # 训练集
    │   ├── val.csv         # 验证集
    │   ├── test.csv        # 测试集
    │   ├── item_meta.csv   # 物品元数据
    │   ├── id_maps/        # ID 映射 (JSON)
    │   └── stats.json      # 统计信息
    └── cross_domain/       # 跨域汇总
```

## 数据字段

**评论数据**: `user_id`, `item_id`, `rating`, `timestamp`, `review_text`, `summary`, `verified`

**物品元数据**: `item_id`, `title`, `brand`, `category`, `description`, `price`, `features`

## 数据源

- SNAP Stanford (优先): `http://snap.stanford.edu/data/amazon/productGraph/`
- DeepYeti UCSD (备用): `http://deepyeti.ucsd.edu/jianmo/amazon/`
- 原始页面: https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/

## 注意事项

- 下载支持断点续传，中断后重新运行即可继续
- SNAP 服务器速度约 10MB/min，总计 ~1.1GB 需 ~2 小时
- 处理后的 ID 映射保存在 `id_maps/`，确保训练推理一致
