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


# --------------------------------------------------------------------------- 嵌套目录
def _write_nested_seed(root: Path, rel: str, seed: int, metrics: dict) -> None:
    d = root / rel / f"seed{seed}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "metrics.json").write_text(json.dumps(metrics), encoding="utf8")


def test_nested_model_dir_aggregates(tmp_path):
    """results/ch3_recall/baselines/{model}/seed{n}/（G1-6 的实际路径）。"""
    for s, v in enumerate([0.10, 0.12, 0.14]):
        _write_nested_seed(tmp_path, "ch3_recall/baselines/lightgcn", s, {"Recall@10": v})

    nums = mt.collect(tmp_path)

    assert nums["recall.baselines.lightgcn.Recall@10.mean"]["value"] == pytest.approx(0.12)
    assert nums["recall.baselines.lightgcn.Recall@10.seeds"]["value"] == [0.10, 0.12, 0.14]
    assert nums["recall.baselines.lightgcn.Recall@10.mean"]["n_seeds"] == 3


def test_two_level_nested_model(tmp_path):
    """results/ch3_recall/cross/{dataset}/{model}/seed{n}/。"""
    for s, v in enumerate([0.2, 0.3]):
        _write_nested_seed(tmp_path, "ch3_recall/cross/TH/lightgcn", s, {"Recall@10": v})

    nums = mt.collect(tmp_path)
    assert nums["recall.cross.TH.lightgcn.Recall@10.mean"]["value"] == pytest.approx(0.25)


def test_top_level_model_key_unchanged(tmp_path):
    """已有的一层结构 key 不能变，否则正文引用全部失效。"""
    _write_seed(tmp_path, "ch3_recall", "ti_lightgcn", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)
    assert nums["recall.ti_lightgcn.Recall@10.mean"]["value"] == 0.5


def test_nested_seed_order_numeric(tmp_path):
    for s in (0, 2, 10):
        _write_nested_seed(tmp_path, "ch3_recall/baselines/m", s, {"Recall@10": s / 100})
    nums = mt.collect(tmp_path)
    assert nums["recall.baselines.m.Recall@10.seeds"]["value"] == [0.0, 0.02, 0.10]


def test_nested_dirty_manifest_skipped(tmp_path):
    _write_nested_seed(tmp_path, "ch3_recall/baselines/m", 0, {"Recall@10": 0.5})
    mf = tmp_path / "ch3_recall/baselines/m/seed0/manifest.json"
    mf.write_text(json.dumps({"git_dirty": True}), encoding="utf8")
    assert mt.collect(tmp_path) == {}


def test_underscore_subdir_skipped_in_aggregation(tmp_path):
    _write_nested_seed(tmp_path, "ch3_recall/_scratch/m", 0, {"Recall@10": 0.99})
    _write_nested_seed(tmp_path, "ch3_recall/baselines/m", 0, {"Recall@10": 0.10})
    nums = mt.collect(tmp_path)
    assert nums["recall.baselines.m.Recall@10.mean"]["value"] == pytest.approx(0.10)
    assert not any("_scratch" in k for k in nums)


# --------------------------------------------------------------------------- 嵌套 JSON
def _write_json(root: Path, rel: str, data: dict) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf8")


def test_collects_json_in_subdir(tmp_path):
    """results/ch5_system/latency/latency.json → sys.latency.P99。"""
    _write_json(tmp_path, "ch5_system/latency/latency.json", {"P99": 83.2})

    nums = mt.collect(tmp_path)
    assert nums["sys.latency.P99"]["value"] == pytest.approx(83.2)


def test_flat_and_nested_json_produce_same_key(tmp_path):
    """平铺 latency.json 与 latency/latency.json 的 key 必须一致。"""
    _write_json(tmp_path, "ch5_system/latency.json", {"P99": 83.2})
    flat = mt.collect(tmp_path)

    other = tmp_path / "nested"
    _write_json(other, "ch5_system/latency/latency.json", {"P99": 83.2})
    nested = mt.collect(other)

    assert set(flat) == set(nested) == {"sys.latency.P99"}


def test_json_subdir_name_is_not_duplicated(tmp_path):
    """文件名与目录同名时不重复出现：loadtest/loadtest.json → sys.loadtest.*。"""
    _write_json(tmp_path, "ch5_system/loadtest/loadtest.json", {"P50": 20.0})
    assert "sys.loadtest.P50" in mt.collect(tmp_path)


def test_deeper_json_path_joined_by_dots(tmp_path):
    _write_json(tmp_path, "ch5_system/latency/per_step/recall.json", {"P99": 12.0})
    assert "sys.latency.per_step.recall.P99" in mt.collect(tmp_path)


def test_nested_json_source_points_to_real_file(tmp_path):
    _write_json(tmp_path, "ch5_system/consistency/consistency.json", {"recall_match": 1.0})
    nums = mt.collect(tmp_path)
    for key, rec in nums.items():
        assert (tmp_path / rec["source"]).exists(), f"{key} 的 source 不存在"


def test_json_inside_seed_dir_not_double_counted(tmp_path):
    """seed 目录里的 metrics.json 只走聚合，不额外走展平。"""
    _write_nested_seed(tmp_path, "ch3_recall/baselines/m", 0, {"Recall@10": 0.5})
    nums = mt.collect(tmp_path)
    assert set(nums) == {
        "recall.baselines.m.Recall@10.mean",
        "recall.baselines.m.Recall@10.std",
        "recall.baselines.m.Recall@10.seeds",
    }


def test_json_underscore_subdir_skipped(tmp_path):
    _write_json(tmp_path, "ch5_system/_draft/x.json", {"P99": 1.0})
    assert mt.collect(tmp_path) == {}


def test_json_in_exp_prefix_dir_is_collected(tmp_path):
    """ch3_recall/cold_start/ti_lightgcn.json 这类非 seed JSON 也要采到。"""
    _write_json(tmp_path, "ch3_recall/cold_start/ti_lightgcn.json", {"Recall@10": 0.07})
    assert "recall.cold_start.ti_lightgcn.Recall@10" in mt.collect(tmp_path)


# --------------------------------------------------------------------------- key 口径（以 S1-d 卡片为准）
def test_value_wrapper_collapses_to_bare_key(tmp_path):
    _write_json(
        tmp_path,
        "profile/IS.json",
        {"gamma0": {"value": 0.0313, "formula": "ln2 / 中位数"}},
    )
    nums = mt.collect(tmp_path)
    assert nums["profile.IS.gamma0"]["value"] == pytest.approx(0.0313)
    assert "profile.IS.gamma0.value" not in nums


def test_value_wrapper_keeps_sibling_numbers(tmp_path):
    _write_json(
        tmp_path,
        "profile/IS.json",
        {"test_ratio": {"value": 0.99, "n_test": 50985}},
    )
    nums = mt.collect(tmp_path)
    assert nums["profile.IS.test_ratio"]["value"] == pytest.approx(0.99)
    assert nums["profile.IS.test_ratio.n_test"]["value"] == 50985


def test_plain_nested_dict_without_value_key(tmp_path):
    _write_json(
        tmp_path,
        "profile/IS.json",
        {"inter_gap_days": {"mean": 165.5, "median": 22.1}},
    )
    nums = mt.collect(tmp_path)
    assert nums["profile.IS.inter_gap_days.mean"]["value"] == pytest.approx(165.5)
    assert nums["profile.IS.inter_gap_days.median"]["value"] == pytest.approx(22.1)


def test_boolean_and_string_not_collected(tmp_path):
    _write_json(tmp_path, "profile/IS.json", {"has_rating": True, "dataset": "IS"})
    assert mt.collect(tmp_path) == {}
