# 数据集说明

## 数据集概览

| 数据集 | 简称 | 用户数 | 物品数 | 交互数 | 稀疏度 | 用途 |
|--------|------|--------|--------|--------|--------|------|
| Industrial & Scientific | IS | ~16,438 | ~10,228 | ~680,000 | >99% | 主实验 |
| Tools & Hardware | TH | - | - | - | 中等稀疏 | 跨域验证 |
| Office Products | OP | - | - | - | 较密集 | 跨域验证 |
| Automotive Jewelry | AJ | - | - | - | - | 跨域验证 (含多行为数据) |

## 数据来源

- **Amazon Review Data (2023)**: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
- **Amazon Review Data (2018)**: https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/

## 目录结构

```
data/
├── README.md              # 本文件
├── download_data.py       # 数据下载脚本
├── prepare_data.py        # 数据预处理脚本
├── quick_start.sh         # 一键下载+处理
├── raw/                   # 原始数据 (下载后生成)
│   ├── Industrial_and_Scientific.json.gz
│   ├── meta_Industrial_and_Scientific.json.gz
│   ├── Tools_and_Home_Improvement.json.gz
│   └── ...
└── processed/             # 处理后数据 (预处理后生成)
    ├── IS/                # 主实验数据
    │   ├── train.csv
    │   ├── val.csv
    │   ├── test.csv
    │   ├── item_meta.csv
    │   ├── id_maps/
    │   └── stats.json
    ├── TH/                # 跨域验证数据
    ├── OP/
    ├── AJ/
    └── cross_domain/
        └── cross_domain_summary.json
```

## 快速开始

```bash
# 1. 安装依赖
pip install pandas numpy pyarrow datasets

# 2. 下载数据 (全部类别)
python download_data.py

# 3. 只下载主实验数据
python download_data.py --categories IS

# 4. 预处理数据 (5-core 过滤)
python prepare_data.py --k-core 5

# 5. 一键执行
bash quick_start.sh
```

## 脚本参数

### download_data.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--categories` | 要下载的类别 (IS/TH/OP/AJ) | 全部 |
| `--source` | 下载来源 (auto/hf/direct/kaggle/manual) | auto |
| `--data-type` | 数据类型 (reviews/meta/both) | both |
| `--dry-run` | 只打印操作不实际下载 | false |

### prepare_data.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--categories` | 要处理的类别 | 全部 |
| `--k-core` | K-core 过滤阈值 (0=不过滤) | 0 |
| `--output-format` | 输出格式 (csv/parquet/both) | both |
| `--stats-only` | 只输出统计信息 | false |
| `--val-ratio` | 验证集比例 | 0.1 |
| `--test-ratio` | 测试集比例 | 0.1 |

## 数据字段说明

### 评论数据 (reviews)

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | str | 用户 ID (reviewerID) |
| item_id | str | 物品 ID (ASIN) |
| rating | float | 评分 (1-5) |
| timestamp | int | Unix 时间戳 |
| review_text | str | 评论文本 (可选) |
| summary | str | 评论摘要 (可选) |
| verified | bool | 是否验证购买 (可选) |

### 物品元数据 (meta)

| 字段 | 类型 | 说明 |
|------|------|------|
| item_id | str | 物品 ID (ASIN) |
| title | str | 商品标题 |
| brand | str | 品牌 |
| category | list | 商品类别 |
| description | str | 商品描述 |
| price | float | 价格 |
| features | list | 商品特征 |

## 注意事项

- 原始数据来自 UCSD McAuley 实验室, deepyeti 服务器已退役
- 推荐通过 HuggingFace 的 McAuley-Lab/Amazon-Reviews-2023 下载
- 2023 版本包含 1996-2023 的数据, 可过滤至 2018 之前得到 2018 版本
- 处理后的 ID 映射保存在 `id_maps/` 目录, 确保训练和推理使用一致的编码
