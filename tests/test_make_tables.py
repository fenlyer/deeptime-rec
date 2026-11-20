"""S1-d 数字管线测试：scripts/make_tables.py

覆盖：
    - 从 seed 目录聚合 metrics.json → 均值/标准差/逐 seed 值
    - key 命名与卡片约定一致
    - 每个数字带 source（真实存在的文件路径）
    - 缺失指标不产生 null key
    - 输出确定性（两次运行字节一致）
    - 空 results/ 不报错，输出空 numbers
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import make_tables as mt  # noqa: E402


# --------------------------------------------------------------------------- 构造
def _write_seed(root: Path, exp: str, model: str, seed: int, metrics: dict) -> None:
    d = root / exp / model / f"seed{seed}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "metrics.json").write_text(json.dumps(metrics), encoding="utf8")


# --------------------------------------------------------------------------- 聚合
def test_aggregates_mean_and_std_over_seeds(tmp_path):
    for s, v in enumerate([0.10, 0.12, 0.11]):
        _write_seed(tmp_path, "ch3_recall", "lightgcn", s, {"Recall@10": v})

    nums = mt.collect(tmp_path)

    assert nums["recall.lightgcn.Recall@10.mean"]["value"] == pytest.approx(0.11)
    assert nums["recall.lightgcn.Recall@10.seeds"]["value"] == [0.10, 0.12, 0.11]
    # 样本标准差（ddof=1）
    assert nums["recall.lightgcn.Recall@10.std"]["value"] == pytest.approx(0.01)


def test_seed_order_is_numeric_not_lexicographic(tmp_path):
    for s in (0, 1, 2, 10):
        _write_seed(tmp_path, "ch3_recall", "m", s, {"Recall@10": s / 100})

    nums = mt.collect(tmp_path)
    assert nums["recall.m.Recall@10.seeds"]["value"] == [0.0, 0.01, 0.02, 0.10]


def test_single_seed_has_null_std(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)
    assert nums["recall.m.Recall@10.std"]["value"] is None


# --------------------------------------------------------------------------- 溯源
def test_every_number_has_existing_source(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)

    for key, rec in nums.items():
        assert rec["source"], f"{key} 缺 source"
        assert (tmp_path / rec["source"]).exists(), f"{key} 的 source 不存在：{rec['source']}"


def test_source_is_relative_posix(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)
    src = nums["recall.m.Recall@10.mean"]["source"]
    assert "\\" not in src
    assert not Path(src).is_absolute()


# --------------------------------------------------------------------------- 缺失
def test_missing_metric_produces_no_key(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)
    assert not any("Recall@20" in k for k in nums)


def test_non_numeric_metric_skipped(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5, "note": "hello"})
    nums = mt.collect(tmp_path)
    assert not any(k.endswith(".note.mean") for k in nums)


# --------------------------------------------------------------------------- 确定性
def test_output_is_deterministic(tmp_path):
    for s in range(3):
        _write_seed(tmp_path, "ch3_recall", "b_model", s, {"Recall@10": 0.1 + s})
        _write_seed(tmp_path, "ch3_recall", "a_model", s, {"Recall@10": 0.2 + s})

    a = mt.dumps(mt.collect(tmp_path))
    b = mt.dumps(mt.collect(tmp_path))
    assert a == b
    # 键按字典序，a_model 在 b_model 之前
    assert a.index("a_model") < a.index("b_model")


# --------------------------------------------------------------------------- 空输入
def test_empty_results_dir_returns_empty(tmp_path):
    nums = mt.collect(tmp_path)
    assert nums == {}
    assert json.loads(mt.dumps(nums)) == {}


def test_ignores_underscore_prefixed_dirs(tmp_path):
    """results/_smoke/ 是冒烟目录，不进正式数字。"""
    _write_seed(tmp_path, "_smoke", "m", 0, {"Recall@10": 0.99})
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.10})

    nums = mt.collect(tmp_path)
    assert nums["recall.m.Recall@10.mean"]["value"] == pytest.approx(0.10)


def test_ignores_dirty_smoke_manifest(tmp_path):
    """manifest.json 标记 dirty 的 run 不进数字（工作区有未提交改动）。"""
    d = tmp_path / "ch3_recall" / "m" / "seed0"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({"Recall@10": 0.5}))
    (d / "manifest.json").write_text(json.dumps({"git_dirty": True}))

    assert mt.collect(tmp_path) == {}


# --------------------------------------------------------------------------- 写盘
def test_write_outputs_expected_files(tmp_path):
    _write_seed(tmp_path, "ch3_recall", "m", 0, {"Recall@10": 0.5})
    out = tmp_path / "out" / "numbers.json"
    mt.write(mt.collect(tmp_path), out)

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf8"))
    assert "recall.m.Recall@10.mean" in data
    assert data["recall.m.Recall@10.mean"]["value"] == 0.5
