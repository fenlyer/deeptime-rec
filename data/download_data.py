#!/usr/bin/env python3
"""
Amazon Review 数据集下载脚本
支持断点续传、多源、并行下载
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 数据源 (按优先级)
SOURCES = {
    "snap": "http://snap.stanford.edu/data/amazon/productGraph/categoryFiles",
    "deepyeti": "http://deepyeti.ucsd.edu/jianmo/amazon",
}

# 下载任务: (文件名, 类别, 类型)
DOWNLOAD_TASKS = [
    ("reviews_Industrial_and_Scientific.json.gz", "Industrial_and_Scientific", "reviews"),
    ("reviews_Tools_and_Home_Improvement.json.gz", "Tools_and_Home_Improvement", "reviews"),
    ("reviews_Office_Products.json.gz", "Office_Products", "reviews"),
    ("reviews_Automotive.json.gz", "Automotive", "reviews"),
    ("meta_Industrial_and_Scientific.json.gz", "Industrial_and_Scientific", "meta"),
    ("meta_Tools_and_Home_Improvement.json.gz", "Tools_and_Home_Improvement", "meta"),
    ("meta_Office_Products.json.gz", "Office_Products", "meta"),
    ("meta_Automotive.json.gz", "Automotive", "meta"),
]

# 预期大小 (MB)
EXPECTED_SIZES = {
    "reviews_Industrial_and_Scientific.json.gz": 46.6,
    "reviews_Tools_and_Home_Improvement.json.gz": 364.0,
    "reviews_Office_Products.json.gz": 238.2,
    "reviews_Automotive.json.gz": 227.4,
    "meta_Industrial_and_Scientific.json.gz": 16.4,
    "meta_Tools_and_Home_Improvement.json.gz": 89.8,
    "meta_Office_Products.json.gz": 45.3,
    "meta_Automotive.json.gz": 87.7,
}


def get_url(filename: str, category: str, dtype: str, source: str) -> str:
    """构建下载 URL"""
    base = SOURCES[source]
    if source == "snap":
        return f"{base}/{filename}"
    elif source == "deepyeti":
        if dtype == "reviews":
            return f"{base}/reviews/{category}.json.gz"
        else:
            return f"{base}/metaFiles/meta_{category}.json.gz"
    return ""


def download_file(filename: str, category: str, dtype: str, source: str, max_retries: int = 3):
    """下载单个文件，支持断点续传"""
    dest = RAW_DIR / filename
    expected_mb = EXPECTED_SIZES.get(filename, 0)
    url = get_url(filename, category, dtype, source)
    
    # 检查是否已完整
    if dest.exists():
        current_mb = dest.stat().st_size / (1024 * 1024)
        if expected_mb > 0 and current_mb >= expected_mb * 0.95:
            return filename, "skip", f"已完整 ({current_mb:.1f}MB)"
    
    for attempt in range(max_retries):
        cmd = [
            "curl", "-L", "-C", "-",  # 断点续传
            "-o", str(dest),
            "--connect-timeout", "15",
            "--max-time", "3600",
            "--retry", "2",
            "--retry-delay", "3",
            "-#",  # 进度条
            url,
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3700)
            
            if dest.exists():
                actual_mb = dest.stat().st_size / (1024 * 1024)
                if expected_mb > 0 and actual_mb >= expected_mb * 0.95:
                    return filename, "ok", f"完成 ({actual_mb:.1f}MB)"
                elif actual_mb > 0:
                    return filename, "partial", f"部分 ({actual_mb:.1f}/{expected_mb:.1f}MB)"
            
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue
    
    return filename, "failed", "下载失败"


def main():
    parser = argparse.ArgumentParser(description="下载 Amazon Review 数据集")
    parser.add_argument("--source", default="snap", choices=list(SOURCES.keys()),
                        help="数据源 (默认: snap)")
    parser.add_argument("--workers", type=int, default=4,
                        help="并行下载数 (默认: 4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示下载列表，不执行")
    args = parser.parse_args()
    
    print("=" * 70)
    print("📦 Amazon Review 数据集下载器")
    print("=" * 70)
    print(f"数据源: {args.source}")
    print(f"并行数: {args.workers}")
    print(f"目标目录: {RAW_DIR}")
    print()
    
    if args.dry_run:
        print("下载列表:")
        for filename, category, dtype in DOWNLOAD_TASKS:
            url = get_url(filename, category, dtype, args.source)
            print(f"  {filename}")
            print(f"    → {url}")
        return 0
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for filename, category, dtype in DOWNLOAD_TASKS:
            f = executor.submit(download_file, filename, category, dtype, args.source)
            futures[f] = filename
        
        for future in as_completed(futures):
            filename, status, msg = future.result()
            results.append((filename, status, msg))
            emoji = {"ok": "✅", "skip": "⏭️", "partial": "⏳", "failed": "❌"}.get(status, "❓")
            print(f"{emoji} {filename}: {msg}")
    
    elapsed = time.time() - start_time
    
    # 汇总
    print()
    print("=" * 70)
    print("📊 下载汇总")
    print("=" * 70)
    
    ok_count = sum(1 for _, s, _ in results if s in ("ok", "skip"))
    partial_count = sum(1 for _, s, _ in results if s == "partial")
    fail_count = sum(1 for _, s, _ in results if s == "failed")
    
    print(f"✅ 完成: {ok_count}/8")
    print(f"⏳ 部分: {partial_count}/8")
    print(f"❌ 失败: {fail_count}/8")
    print(f"⏱️  耗时: {elapsed/60:.1f} 分钟")
    
    # 文件列表
    print()
    print("📁 文件列表:")
    total_mb = 0
    for filename, _, _ in DOWNLOAD_TASKS:
        fpath = RAW_DIR / filename
        if fpath.exists():
            mb = fpath.stat().st_size / (1024 * 1024)
            total_mb += mb
            exp = EXPECTED_SIZES[filename]
            pct = mb / exp * 100
            print(f"  {filename}: {mb:.1f}/{exp:.1f}MB ({pct:.0f}%)")
        else:
            print(f"  {filename}: 缺失")
    
    total_exp = sum(EXPECTED_SIZES.values())
    print(f"\n  总计: {total_mb:.0f}MB / {total_exp:.0f}MB ({total_mb/total_exp*100:.1f}%)")
    
    if partial_count > 0:
        print("\n💡 提示: 重新运行可断点续传")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
