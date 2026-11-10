#!/bin/bash
# 一键下载 + 预处理 Amazon Review 数据集
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Amazon Review 数据集一键下载与处理"
echo "============================================"

# 1. 安装依赖
echo ""
echo "📦 检查依赖..."
pip3 install -q pandas numpy pyarrow 2>/dev/null || true

# 2. 下载数据 (断点续传, 4 并行)
echo ""
echo "⬇️  下载数据..."
python3 download_data.py --workers 4

# 3. 预处理 (5-core 过滤)
echo ""
echo "🔧 预处理数据 (5-core 过滤)..."
python3 prepare_data.py --k-core 5

# 4. 验证
echo ""
echo "✅ 检查输出..."
for dir in processed/*/; do
    [ -d "$dir" ] && echo "  📁 $dir → $(ls "$dir"*.csv 2>/dev/null | wc -l | tr -d ' ') 个 CSV 文件"
done

echo ""
echo "🎉 全部完成!"
