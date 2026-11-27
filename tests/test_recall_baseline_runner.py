"""召回基线 runner 测试（S-recall-base）

覆盖：
    - 配置构造：冻结切分（benchmark_filename）、指标/topk、seed、epochs=200、
      早停 patience=20 逐项传入 RecBole config
    - 打分 → per_user：与 eval/full_rank.py 的悲观并列 + 屏蔽训练∩验证口径逐用户一致
    - 扁平模型（BPR 这类 full_sort_predict 返回扁平的）打分 reshape 正确
    - configs/recall/*.yaml 存在且口径与卡片一致（模型 → RecBole 类名映射）
    - summary.csv 跨 seed 均值/标准差

本文件不导入 recbole（本机 research 环境没装），runner 里的 recbole 导入必须在函数内。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "experiments"))

import run_recall_baseline as rb  # noqa: E402
from eval.full_rank import full_rank as eval_full_rank  # noqa: E402

CONFIG_DIR = REPO_ROOT / "configs" / "recall"


# --------------------------------------------------------------------------- 配置
@pytest.mark.parametrize("model_key,recbole_name", [
    ("bprmf", "BPR"),
    ("ngcf", "NGCF"),
    ("lightgcn", "LightGCN"),
    ("sgl", "SGL"),
    ("simgcl", "SimGCL"),
])
def test_model_mapping(model_key, recbole_name):
    assert rb.RECBOLE_MODEL[model_key] == recbole_name


@pytest.mark.parametrize("model_key", ["bprmf", "ngcf", "lightgcn", "sgl", "simgcl"])
def test_config_file_exists(model_key):
    assert (CONFIG_DIR / f"{model_key}.yaml").exists(), f"缺 configs/recall/{model_key}.yaml"


@pytest.mark.parametrize("model_key", ["bprmf", "ngcf", "lightgcn", "sgl", "simgcl"])
def test_config_card_alignment(model_key):
    """口径与卡片一致：embedding 64 / batch 2048 / 200 epoch / patience 20 / 5 seed。"""
    cfg = rb.load_model_config(model_key, CONFIG_DIR)
    assert cfg["embedding_size"] == 64
    assert cfg["train_batch_size"] == 2048
    assert cfg["epochs"] == 200
    assert cfg["stopping_step"] == 20
    assert cfg["topk"] == [10, 20]
    assert cfg["metrics"] == ["Recall", "NDCG"]
    assert cfg["seeds"] == [0, 1, 2, 3, 4]


def test_build_config_freezes_split_and_seed():
    """冻结切分模式、seed、GPU 开关都要落到 RecBole config_dict 里。"""
    cfg = rb.load_model_config("lightgcn", CONFIG_DIR)
    d = rb.build_config("lightgcn", cfg, seed=3, data_path=Path("data/recbole"),
                        use_gpu=False)
    assert d["model"] == "LightGCN"
    assert d["seed"] == 3
    assert d["benchmark_filename"] == ["train", "val", "test"]
    assert d["eval_args"]["split"] == {"mode": "custom"}
    assert d["eval_args"]["group_by"] == "user"
    assert d["metrics"] == ["Recall", "NDCG"]
    assert d["topk"] == [10, 20]
    assert d["epochs"] == 200
    assert d["stopping_step"] == 20
    assert d["use_gpu"] is False
    assert str(d["data_path"]) == "data/recbole"
    assert "seeds" not in d  # 卡片自己的字段不能泄漏进 RecBole config


def test_build_config_eval_batch_size_not_overridden_by_yaml():
    """配置里的 eval_batch_size（4096）不能覆盖 runner 算出的值。

    RecBole 每批用户数 = eval_batch_size // item_num。item_num=25849 时 4096 → 每批 1 用户，
    50985 批会让打分阶段慢到不可用（2026-11-27 冒烟实测退化）。
    """
    cfg = rb.load_model_config("lightgcn", CONFIG_DIR)
    assert cfg["eval_batch_size"] == 4096  # yaml 里确实写着小值
    d = rb.build_config("lightgcn", cfg, seed=0, data_path=Path("data/recbole"), use_gpu=False)
    assert d["eval_batch_size"] > 25849, "eval_batch_size 必须大于物品数，否则每批只有 1 用户"
    assert d["eval_batch_size"] // 25849 >= 64, f"每批用户数太少：{d['eval_batch_size'] // 25849}"


def test_build_config_does_not_mutate_source():
    cfg = rb.load_model_config("sgl", CONFIG_DIR)
    before = dict(cfg)
    rb.build_config("sgl", cfg, seed=1, data_path=Path("data/recbole"), use_gpu=True)
    assert cfg == before


# --------------------------------------------------------------------------- 打分 → per_user
def _tiny_world():
    """3 用户 / 5 物品的小世界，用户 0 的测试物品与另一物品同分（验证悲观并列）。

    processed idx 与 RecBole 内部编号相同（不模拟 [PAD] 偏移，那张由真实 run 验证）。
    """
    train = pd.DataFrame({"user_idx": [0, 0, 1, 2], "item_idx": [0, 1, 1, 2]})
    val = pd.DataFrame({"user_idx": [0, 1], "item_idx": [3, 3]})
    test = pd.DataFrame({"user_idx": [0, 1, 2], "item_idx": [2, 4, 4]})
    return train, val, test


def _conduct_from(train, val, test, item_to_col=None):
    """按 runner 的方式从三个 DataFrame 构造 conduct（屏蔽集 + 测试索引）。"""
    item_to_col = item_to_col or {i: i for i in range(5)}
    shield = {}
    for frame in (train, val):
        for u, i in zip(frame.user_idx.astype(int), frame.item_idx.astype(int)):
            col = item_to_col.get(int(i))
            if col is not None:
                shield.setdefault(int(u), set()).add(col)
    shield = {u: np.array(sorted(c)) for u, c in shield.items()}
    test_by_user = {}
    for u, i in zip(test.user_idx.astype(int), test.item_idx.astype(int)):
        test_by_user.setdefault(int(u), []).append(int(i))
    return {"shield": shield, "test_by_user": test_by_user, "item_to_col": item_to_col}


def test_scores_to_per_user_matches_eval_full_rank():
    """runner 的向量化排名必须与 eval/full_rank.py 逐用户完全一致。"""
    train, val, test = _tiny_world()
    n_users, n_items = 3, 5

    # 构造 (用户, 测试物品) 的打分矩阵
    scores = np.array([
        [0.0, 0.1, 0.5, 0.0, 0.5],   # user 0：测试物品 2 与物品 4 同分（0.5）
        [0.3, 0.1, 0.0, 0.0, 0.2],   # user 1
        [0.1, 0.2, 0.3, 0.4, 0.9],   # user 2
    ], dtype=np.float64)

    got = rb.scores_to_per_user(scores=scores, conduct=_conduct_from(train, val, test))

    # 同一份打分交给 eval/full_rank（长表形式、pessimistic 并列）
    all_items = sorted(set(train.item_idx) | set(val.item_idx) | set(test.item_idx))
    scores_long = pd.DataFrame([
        {"user_id": str(u), "item_id": str(i), "score": float(scores[u, i])}
        for u in range(n_users)
        for i in all_items
    ])
    shielded = {(str(r.user_idx), str(r.item_idx))
                for r in pd.concat([train[["user_idx", "item_idx"]],
                                    val[["user_idx", "item_idx"]]]).itertuples()}
    test_named = test.assign(user_id=test.user_idx.astype(str),
                             item_id=test.item_idx.astype(str))
    want = eval_full_rank(scores=scores_long, all_items=[str(i) for i in all_items],
                          shielded=shielded, test_df=test_named, tie="pessimistic")

    want_rank = dict(zip(want["user_id"], want["rank"]))
    got_rank = dict(zip(got["user_id"].astype(str), got["rank"]))
    assert got_rank == want_rank


def test_scores_to_per_user_pessimistic_tie():
    """用户 0 的测试物品与物品 4 同分：悲观排名把同分者算在前面。"""
    train, val, test = _tiny_world()
    scores = np.array([
        [0.0, 0.1, 0.5, 0.0, 0.5],
        [0.3, 0.1, 0.0, 0.0, 0.2],
        [0.1, 0.2, 0.3, 0.4, 0.9],
    ])
    got = rb.scores_to_per_user(scores=scores, conduct=_conduct_from(train, val, test))
    # user0 候选 = {2, 4}（0/1/3 被屏蔽），同分 → rank = 1 + 0 + 1 = 2
    assert float(got.loc[got.user_id == 0, "rank"].iloc[0]) == 2.0


def test_scores_to_per_user_shields_train_and_val():
    """训练集与验证集物品都屏蔽：分数再高也不参与排名。"""
    train = pd.DataFrame({"user_idx": [0, 0, 1, 2], "item_idx": [0, 1, 1, 2]})
    val = pd.DataFrame({"user_idx": [0, 1], "item_idx": [3, 3]})
    test = pd.DataFrame({"user_idx": [0, 1, 2], "item_idx": [2, 4, 4]})
    # user0 的候选只有 {2, 4}；把训练/验证物品(0,1,3)打成满分，若未屏蔽 rank 会 >2
    scores = np.array([
        [9.0, 9.0, 0.5, 9.0, 0.1],
        [9.0, 9.0, 9.0, 9.0, 0.2],
        [9.0, 9.0, 9.0, 9.0, 0.9],
    ])
    got = rb.scores_to_per_user(scores=scores, conduct=_conduct_from(train, val, test))
    # user0 候选 {2, 4}：0.5 > 0.1 → rank 1
    assert float(got.loc[got.user_id == 0, "rank"].iloc[0]) == 1.0
    # user1 候选 {0, 2, 4}（1 训练、3 验证被屏蔽）：0.2 低于 9.0 两个 → rank 3
    assert float(got.loc[got.user_id == 1, "rank"].iloc[0]) == 3.0


def test_scores_to_per_user_output_columns():
    train, val, test = _tiny_world()
    scores = np.zeros((3, 5))
    got = rb.scores_to_per_user(scores=scores, conduct=_conduct_from(train, val, test))
    assert set(got.columns) >= {"user_id", "test_item", "rank"}


def test_scores_to_per_user_respects_internal_id_mapping():
    """processed item_idx → 矩阵列号走映射，不靠 offset 猜。"""
    train = pd.DataFrame({"user_idx": [0], "item_idx": [101]})
    val = pd.DataFrame({"user_idx": [0], "item_idx": [102]})
    test = pd.DataFrame({"user_idx": [0], "item_idx": [103]})
    # 物品 101/102/103 对应矩阵第 1/2/3 列（第 0 列是 [PAD]）
    scores = np.array([[0.0, 0.9, 0.8, 0.1]])
    got = rb.scores_to_per_user(scores=scores, conduct=_conduct_from(
        train, val, test, item_to_col={101: 1, 102: 2, 103: 3}))
    assert float(got.loc[got.user_id == 0, "rank"].iloc[0]) == 1.0


# --------------------------------------------------------------------------- 按批计算
def test_ranks_for_users_batch_equals_full():
    """分批算（每批一部分用户）与一次性全量算，结果必须逐用户一致。

    per_user_from_model 按批算以避免 10 GB 打分矩阵驻留内存，
    所以这个等价性是那条优化的正确性前提。
    """
    train, val, test = _tiny_world()
    scores = np.array([
        [0.0, 0.1, 0.5, 0.0, 0.5],
        [0.3, 0.1, 0.0, 0.0, 0.2],
        [0.1, 0.2, 0.3, 0.4, 0.9],
    ])
    kw = _conduct_from(train, val, test)

    full = rb.scores_to_per_user(scores=scores, conduct=kw)
    parts = [rb.ranks_for_users(scores[i:i + 1], np.array([i]), kw["shield"],
                                kw["test_by_user"], kw["item_to_col"]) for i in range(3)]
    batched = pd.concat(parts, ignore_index=True)

    assert dict(zip(batched.user_id, batched["rank"])) == \
           dict(zip(full.user_id, full["rank"]))
    assert sorted(batched.user_id) == sorted(full.user_id)


def test_ranks_for_users_skips_users_without_test_row():
    """某个用户块里若没有测试行，不产生 per_user 行（也不报错）。"""
    train, val, test = _tiny_world()
    kw = _conduct_from(train, val, test)
    scores = np.zeros((3, 5))
    got = rb.ranks_for_users(scores, np.array([0]), kw["shield"],
                             kw["test_by_user"], kw["item_to_col"])
    assert len(got) == 1


def test_ranks_for_users_no_shield_path():
    """用户没有屏蔽物品时走无屏蔽分支，结果与全屏蔽分支一致。"""
    kw = {"shield": {}, "test_by_user": {0: [4]}, "item_to_col": {i: i for i in range(5)}}
    scores = np.array([[0.0, 0.1, 0.5, 0.0, 0.9]])
    got = rb.ranks_for_users(scores, np.array([0]), kw["shield"],
                             kw["test_by_user"], kw["item_to_col"])
    # 无屏蔽：0.9 最大 → rank 1
    assert float(got["rank"].iloc[0]) == 1.0


def test_reshape_flat_scores():
    """BPR 的 full_sort_predict 返回扁平数组，必须 reshape 成 (n_rows, n_items)。"""
    flat = np.arange(15, dtype=np.float64)
    got = rb.reshape_scores(flat, n_rows=3, n_items=5)
    assert got.shape == (3, 5)
    assert got[1, 2] == flat[1 * 5 + 2]

    already = flat.reshape(3, 5)
    np.testing.assert_array_equal(rb.reshape_scores(already, 3, 5), already)


# --------------------------------------------------------------------------- summary
def test_summary_aggregates_mean_and_std(tmp_path):
    for s, v in enumerate([0.10, 0.12, 0.14]):
        d = tmp_path / "lightgcn" / f"seed{s}"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text(
            f'{{"Recall@10": {v}, "NDCG@10": {v / 2}}}', encoding="utf8")

    import json
    rows = rb.collect_summary_rows(tmp_path)
    by_key = {(r["model"], r["metric"]): r for r in rows}
    r = by_key[("lightgcn", "Recall@10")]
    assert r["n_seeds"] == 3
    assert r["mean"] == pytest.approx(0.12)
    assert r["std"] == pytest.approx(np.std([0.10, 0.12, 0.14], ddof=1))

    df = pd.DataFrame(rows)
    assert {"model", "metric", "mean", "std", "n_seeds"} <= set(df.columns)


def test_summary_skips_dirty_runs(tmp_path):
    import json
    for s in (0, 1):
        d = tmp_path / "lightgcn" / f"seed{s}"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text(json.dumps({"Recall@10": 0.5}), encoding="utf8")
    (tmp_path / "lightgcn" / "seed1" / "manifest.json").write_text(
        json.dumps({"git_dirty": True}), encoding="utf8")

    rows = rb.collect_summary_rows(tmp_path)
    assert [(r["model"], r["n_seeds"]) for r in rows] == [("lightgcn", 1)]