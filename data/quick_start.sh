#!/bin/bash
# 一键下载和处理 Amazon Review 数据集
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Amazon Review 数据集一键下载与处理"
echo "============================================"

# 1. 检查 Python 依赖
echo ""
echo "📦 检查依赖..."
pip install -q pandas numpy pyarrow 2>/dev/null || {
    echo "⚠️  pip install 失败, 尝试 conda..."
    conda install -y -q pandas numpy pyarrow 2>/dev/null || true
}

# 检查 datasets 库 (HuggingFace)
python3 -c "import datasets" 2>/dev/null || {
    echo "📦 安装 HuggingFace datasets..."
    pip install -q datasets
}

# 2. 下载数据
echo ""
echo "⬇️  下载数据 (HuggingFace 源)..."
python3 download_data.py --source hf

# 3. 预处理 (5-core 过滤)
echo ""
echo "🔧 预处理数据 (5-core 过滤)..."
python3 prepare_data.py --k-core 5

# 4. 验证
echo ""
echo "✅ 检查输出..."
for dir in processed/*/; do
    if [ -d "$dir" ]; then
        count=$(ls "$dir"*.csv 2>/dev/null | wc -l)
        echo "  📁 $dir → ${count} 个 CSV 文件"
    fi
done

echo ""
echo "🎉 全部完成!"
echo "  原始数据:   $SCRIPT_DIR/raw/"
echo "  处理后数据: $SCRIPT_DIR/processed/"
