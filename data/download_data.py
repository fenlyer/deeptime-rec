#!/usr/bin/env python3
"""
Amazon Review 数据集下载脚本
==============================
数据集来源:
  - Amazon Review Data (2023): McAuley-Lab/Amazon-Reviews-2023 (HuggingFace)
  - Amazon Review Data (2018 备用): 需要手动下载
包含类别:
  - Industrial_and_Scientific (IS) → 主实验
  - Tools_and_Home_Improvement  (TH) → 跨域验证
  - Office_Products             (OP) → 跨域验证
  - Automotive                  (AJ) → 跨域验证 (含原生多行为数据)

用法:
  python download_data.py                   # 下载全部类别
  python download_data.py --categories IS   # 只下载主实验数据
  python download_data.py --source hf       # 仅用 HuggingFace 下载
  python download_data.py --source kaggle   # 仅用 Kaggle 下载 (需要 kaggle API)
  python download_data.py --dry-run         # 只打印将要执行的操作
"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 数据集配置: key=短名, value=HuggingFace 类别名
CATEGORIES = {
    "IS": "Industrial_and_Scientific",
    "TH": "Tools_and_Home_Improvement",
    "OP": "Office_Products",
    "AJ": "Automotive",
}

CATEGORY_DESCRIPTIONS = {
    "IS": "Industrial & Scientific (主实验, ~16K 用户, ~10K 物品, ~680K 交互)",
    "TH": "Tools & Hardware (跨域验证, 中等稀疏)",
    "OP": "Office Products (跨域验证, 较密集)",
    "AJ": "Automotive Jewelry (跨域验证, 含原生多行为数据)",
}

# HuggingFace 数据集配置名格式
HF_REVIEW_CONFIG = "raw_review_{category}"
HF_META_CONFIG = "raw_meta_{category}"

# 备用直接下载 URL (2018 版, deepyeti 服务器已退役但部分 CDN 可能仍可用)
DIRECT_URLS = {
    "reviews": [
        "http://snap.stanford.edu/data/amazon/productGraph/categoryFiles/reviews_{category}.json.gz",
        "http://deepyeti.ucsd.edu/jianmo/amazon/reviews/{category}.json.gz",
        "https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/categoryFiles/{category}.json.gz",
    ],
    "meta": [
        "http://snap.stanford.edu/data/amazon/productGraph/categoryFiles/meta_{category}.json.gz",
        "http://deepyeti.ucsd.edu/jianmo/amazon/metaFiles/meta_{category}.json.gz",
        "https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/metaFiles/meta_{category}.json.gz",
    ],
}


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "📦", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}.get(level, "ℹ️")
    print(f"{prefix} [{level}] {msg}")


def file_size_mb(path: Path) -> float:
    if path.exists():
        return path.stat().st_size / (1024 * 1024)
    return 0.0


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, desc: str = "", timeout: int = 30) -> bool:
    """用 urllib 下载文件, 带进度显示"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DeepTimeRec/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 65536
            tmp_path = dest.with_suffix(dest.suffix + ".tmp")
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        mb = downloaded / (1024 * 1024)
                        print(f"\r  ⬇️  {desc}: {mb:.1f}MB / {total/(1024*1024):.1f}MB ({pct:.0f}%)", end="", flush=True)
            print()
            shutil.move(str(tmp_path), str(dest))
            return True
    except Exception as e:
        log(f"下载失败 {url}: {e}", "WARN")
        return False


def try_direct_download(category: str, data_type: str) -> Path | None:
    """尝试从备用 URL 直接下载"""
    urls = DIRECT_URLS.get(data_type, [])
    suffix = ".json.gz"
    if data_type == "meta":
        filename = f"meta_{category}{suffix}"
    else:
        filename = f"{category}{suffix}"

    dest = RAW_DIR / filename
    if dest.exists() and file_size_mb(dest) > 1:
        log(f"已存在: {dest.name} ({file_size_mb(dest):.1f}MB)", "OK")
        return dest

    for url in urls:
        url = url.format(category=category)
        log(f"尝试下载: {url}")
        if download_file(url, dest, desc=filename):
            if dest.exists() and file_size_mb(dest) > 0.1:
                log(f"下载成功: {dest.name} ({file_size_mb(dest):.1f}MB)", "OK")
                return dest
            else:
                dest.unlink(missing_ok=True)

    return None


def download_from_huggingface(category: str, data_type: str) -> Path | None:
    """从 HuggingFace 下载数据 (流式读取后保存)"""
    try:
        from datasets import load_dataset
    except ImportError:
        log("需要安装 datasets 库: pip install datasets", "WARN")
        return False

    config_name = HF_REVIEW_CONFIG.format(category=category) if data_type == "reviews" else HF_META_CONFIG.format(category=category)

    suffix = ".json.gz"
    if data_type == "meta":
        filename = f"meta_{category}{suffix}"
    else:
        filename = f"{category}{suffix}"

    dest = RAW_DIR / filename
    if dest.exists() and file_size_mb(dest) > 1:
        log(f"已存在: {dest.name} ({file_size_mb(dest):.1f}MB)", "OK")
        return dest

    log(f"从 HuggingFace 下载: {config_name}")
    log(f"流式加载中, 请耐心等待...", "INFO")

    try:
        dataset = load_dataset(
            "McAuley-Lab/Amazon-Reviews-2023",
            config_name,
            split="full",
            streaming=True,
            trust_remote_code=True,
        )

        records = []
        count = 0
        for example in dataset:
            records.append(json.dumps(example, ensure_ascii=False))
            count += 1
            if count % 100000 == 0:
                log(f"已读取 {count:,} 条记录...")

        log(f"共读取 {count:,} 条记录, 正在压缩写入...")

        with gzip.open(dest, "wt", encoding="utf-8") as f:
            for record in records:
                f.write(record + "\n")

        log(f"保存完成: {dest.name} ({file_size_mb(dest):.1f}MB)", "OK")
        return dest

    except Exception as e:
        log(f"HuggingFace 下载失败: {e}", "WARN")
        return None


def download_from_kaggle() -> bool:
    """从 Kaggle 下载 Amazon Reviews 2018 数据集"""
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", "rogate16/amazon-reviews-2018-full-dataset"],
            capture_output=True, text=True, cwd=str(RAW_DIR),
        )
        if result.returncode != 0:
            log(f"Kaggle 下载失败: {result.stderr}", "WARN")
            return False
        log("Kaggle 数据集已下载, 正在解压...", "OK")
        subprocess.run(["unzip", "-o", "*.zip"], cwd=str(RAW_DIR), shell=True, capture_output=True)
        return True
    except FileNotFoundError:
        log("未安装 kaggle CLI: pip install kaggle", "WARN")
        return False


def download_category(short_name: str, source: str = "auto", dry_run: bool = False) -> dict:
    """下载单个类别的 reviews + meta 数据"""
    full_name = CATEGORIES[short_name]
    desc = CATEGORY_DESCRIPTIONS[short_name]
    result = {"short": short_name, "full": full_name, "reviews": None, "meta": None}

    log(f"{'='*60}")
    log(f"处理: [{short_name}] {desc}")
    log(f"类别全名: {full_name}")
    log(f"{'='*60}")

    for data_type in ["reviews", "meta"]:
        if dry_run:
            log(f"[DRY-RUN] 将下载 {data_type}: {full_name}")
            continue

        downloaded = None

        if source in ("auto", "direct"):
            log(f"尝试直接下载 {data_type}...")
            downloaded = try_direct_download(full_name, data_type)

        if downloaded is None and source in ("auto", "hf"):
            log(f"尝试从 HuggingFace 下载 {data_type}...")
            downloaded = download_from_huggingface(full_name, data_type)

        if downloaded is None:
            log(f"⚠️  {data_type} 下载失败: {full_name}", "WARN")
            log(f"  请手动下载: https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/", "WARN")
            result[data_type] = None
        else:
            result[data_type] = str(downloaded)

    return result


def print_manual_instructions():
    """打印手动下载指南"""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║             手动下载指南                                  ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  方法 1: 官方数据表单 (推荐)                              ║
║  访问: https://cseweb.ucsd.edu/~jmcauley/datasets/       ║
║        amazon_v2/index.html                              ║
║  填写表单后获取下载链接                                    ║
║                                                          ║
║  方法 2: HuggingFace (2023 版, 含 2018 数据)             ║
║  https://huggingface.co/datasets/                        ║
║    McAuley-Lab/Amazon-Reviews-2023                       ║
║                                                          ║
║  方法 3: Kaggle (2018 版)                                ║
║  pip install kaggle                                      ║
║  kaggle datasets download -d                              ║
║    rogate16/amazon-reviews-2018-full-dataset             ║
║                                                          ║
║  方法 4: SNAP Stanford (旧版 2014)                       ║
║  http://snap.stanford.edu/data/                          ║
║    amazon/productGraph/                                  ║
║                                                          ║
║  下载后放入: {str(RAW_DIR):<44s}  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Amazon Review 数据集下载")
    parser.add_argument("--categories", nargs="+", choices=list(CATEGORIES.keys()),
                        default=list(CATEGORIES.keys()),
                        help="要下载的类别, 默认全部")
    parser.add_argument("--source", choices=["auto", "hf", "direct", "kaggle", "manual"],
                        default="auto",
                        help="下载来源: auto=自动选择, hf=HuggingFace, direct=直接URL, kaggle=Kaggle, manual=仅打印手动指南")
    parser.add_argument("--data-type", choices=["reviews", "meta", "both"], default="both",
                        help="下载数据类型: reviews=评论, meta=元数据, both=两者")
    parser.add_argument("--dry-run", action="store_true", help="只打印操作, 不实际下载")
    args = parser.parse_args()

    if args.source == "manual":
        print_manual_instructions()
        return

    log("Amazon Review 数据集下载器")
    log(f"目标目录: {RAW_DIR}")
    log(f"下载来源: {args.source}")
    log(f"类别: {', '.join(args.categories)}")
    print()

    results = []
    for short_name in args.categories:
        result = download_category(short_name, source=args.source, dry_run=args.dry_run)
        results.append(result)

    # 打印下载汇总
    print(f"\n{'='*60}")
    log("下载汇总")
    print(f"{'='*60}")
    print(f"{'类别':<6} {'评论':>8} {'元数据':>8} {'状态':<10}")
    print("-" * 40)
    for r in results:
        rev_status = "✅" if r["reviews"] else "❌"
        meta_status = "✅" if r["meta"] else "❌"
        overall = "✅ 完成" if r["reviews"] and r["meta"] else "⚠️ 部分" if r["reviews"] or r["meta"] else "❌ 失败"
        print(f"[{r['short']}] {r['full']:<35s} {rev_status:>4s} {meta_status:>4s}   {overall}")

    # 检查是否有失败的
    any_failed = any(not r["reviews"] and not r["meta"] for r in results)
    if any_failed:
        print()
        print_manual_instructions()


if __name__ == "__main__":
    main()
