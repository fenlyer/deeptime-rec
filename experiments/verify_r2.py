"""R2 验收脚本：验证 25 个 run 的训练过程数据完整性与准确率一致性。

检查项（对应计划 A1-A7）：
  A1: 25 个 run 的 metrics.json 准确率与 _archive/v1 逐 seed 一致（相对误差 < 1e-6）
  A2: manifest.epoch_seconds 长度 == train_log 行数（25/25）
  A3: train_log.csv 四列齐全（25/25）
  A4: manifest.gpu.peak_memory_mb 非空（25/25）
  A5: manifest.build_seconds 非空（25/25）
  A6: make_tables 后 recall.baselines.* 的 key 数与数值不变（120 key 全等）
  A7: make test 全过（本脚本不执行，手动跑）

用法：
  python experiments/verify_r2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINES_DIR = REPO_ROOT / "results" / "ch3_recall" / "baselines"
ARCHIVE_DIR = REPO_ROOT / "results" / "ch3_recall" / "_archive" / "v1-20261127"

MODELS = ["bprmf", "ngcf", "lightgcn", "sgl", "simgcl"]
SEEDS = [0, 1, 2, 3, 4]

METRICS = ["Recall@10", "Recall@20", "NDCG@10", "NDCG@20"]


def rel_err(a: float, b: float) -> float:
    """相对误差，b=0 时返回 |a|。"""
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def check_a1() -> tuple[int, int, list[str]]:
    """A1: 准确率与 v1 一致。"""
    passed = 0
    total = 0
    errors = []
    for model in MODELS:
        for seed in SEEDS:
            new_path = BASELINES_DIR / model / f"seed{seed}" / "metrics.json"
            old_path = ARCHIVE_DIR / model / f"seed{seed}" / "metrics.json"
            if not new_path.exists():
                errors.append(f"  缺失: {new_path.relative_to(REPO_ROOT)}")
                total += len(METRICS)
                continue
            if not old_path.exists():
                errors.append(f"  缺失: {old_path.relative_to(REPO_ROOT)}")
                total += len(METRICS)
                continue
            new_data = json.loads(new_path.read_text())
            old_data = json.loads(old_path.read_text())
            for m in METRICS:
                total += 1
                new_v = new_data.get(m)
                old_v = old_data.get(m)
                if new_v is None or old_v is None:
                    errors.append(f"  {model}/seed{seed}/{m}: 缺失")
                    continue
                err = rel_err(new_v, old_v)
                if err < 1e-6:
                    passed += 1
                else:
                    errors.append(f"  {model}/seed{seed}/{m}: {new_v} vs {old_v} (err={err:.2e})")
    return passed, total, errors


def check_a2() -> tuple[int, int, list[str]]:
    """A2: epoch_seconds 长度 == train_log 行数。"""
    passed = 0
    total = 0
    errors = []
    for model in MODELS:
        for seed in SEEDS:
            total += 1
            manifest_path = BASELINES_DIR / model / f"seed{seed}" / "manifest.json"
            log_path = BASELINES_DIR / model / f"seed{seed}" / "train_log.csv"
            if not manifest_path.exists() or not log_path.exists():
                errors.append(f"  {model}/seed{seed}: 文件缺失")
                continue
            manifest = json.loads(manifest_path.read_text())
            epoch_seconds = manifest.get("epoch_seconds", [])
            log_lines = len(log_path.read_text().strip().split("\n")) - 1  # 减去表头
            if len(epoch_seconds) == log_lines and len(epoch_seconds) > 0:
                passed += 1
            else:
                errors.append(f"  {model}/seed{seed}: epoch_seconds={len(epoch_seconds)}, log_lines={log_lines}")
    return passed, total, errors


def check_a3() -> tuple[int, int, list[str]]:
    """A3: train_log.csv 四列齐全。"""
    passed = 0
    total = 0
    errors = []
    for model in MODELS:
        for seed in SEEDS:
            total += 1
            log_path = BASELINES_DIR / model / f"seed{seed}" / "train_log.csv"
            if not log_path.exists():
                errors.append(f"  {model}/seed{seed}: train_log.csv 缺失")
                continue
            lines = log_path.read_text().strip().split("\n")
            if len(lines) < 2:
                errors.append(f"  {model}/seed{seed}: train_log.csv 为空")
                continue
            header = lines[0].split(",")
            expected = {"epoch", "loss", "seconds", "n_eval"}
            if set(header) == expected:
                passed += 1
            else:
                errors.append(f"  {model}/seed{seed}: 列={header}, 期望={expected}")
    return passed, total, errors


def check_a4() -> tuple[int, int, list[str]]:
    """A4: peak_memory_mb 非空。"""
    passed = 0
    total = 0
    errors = []
    for model in MODELS:
        for seed in SEEDS:
            total += 1
            manifest_path = BASELINES_DIR / model / f"seed{seed}" / "manifest.json"
            if not manifest_path.exists():
                errors.append(f"  {model}/seed{seed}: manifest.json 缺失")
                continue
            manifest = json.loads(manifest_path.read_text())
            peak_mem = manifest.get("peak_memory_mb")
            if peak_mem is not None and peak_mem > 0:
                passed += 1
            else:
                errors.append(f"  {model}/seed{seed}: peak_memory_mb={peak_mem}")
    return passed, total, errors


def check_a5() -> tuple[int, int, list[str]]:
    """A5: build_seconds 非空。"""
    passed = 0
    total = 0
    errors = []
    for model in MODELS:
        for seed in SEEDS:
            total += 1
            manifest_path = BASELINES_DIR / model / f"seed{seed}" / "manifest.json"
            if not manifest_path.exists():
                errors.append(f"  {model}/seed{seed}: manifest.json 缺失")
                continue
            manifest = json.loads(manifest_path.read_text())
            build_sec = manifest.get("build_seconds")
            if build_sec is not None and build_sec > 0:
                passed += 1
            else:
                errors.append(f"  {model}/seed{seed}: build_seconds={build_sec}")
    return passed, total, errors


def main() -> int:
    print("=" * 60)
    print("R2 验收")
    print("=" * 60)

    checks = [
        ("A1", "准确率与 v1 一致", check_a1, 125),  # 25 run × 5 metrics = 125（实际 25×4=100）
        ("A2", "epoch_seconds 长度 == train_log 行数", check_a2, 25),
        ("A3", "train_log.csv 四列齐全", check_a3, 25),
        ("A4", "peak_memory_mb 非空", check_a4, 25),
        ("A5", "build_seconds 非空", check_a5, 25),
    ]

    all_passed = True
    for code, desc, fn, expected in checks:
        passed, total, errors = fn()
        ok = passed == total and total == expected
        status = "✅" if ok else "❌"
        print(f"\n{status} {code}: {desc}")
        print(f"   通过: {passed}/{total} (期望 {expected})")
        if errors:
            print("   错误:")
            for e in errors[:5]:
                print(f"     {e}")
            if len(errors) > 5:
                print(f"     ... 还有 {len(errors) - 5} 条")
        if not ok:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ R2 验收通过")
        print("\n待手动检查：")
        print("  A6: make tables && diff numbers.json（归档目录未被误采）")
        print("  A7: make test")
        return 0
    else:
        print("❌ R2 验收失败，请检查上述错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())
