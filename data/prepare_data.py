#!/usr/bin/env python3
"""
Amazon Review 2023 / Alibaba IJCAI15 数据预处理脚本
====================================================
对齐《整改V7》5.1.1「数据集选取与说明」与 4.1.2 式(4-1) 的预处理口径。

处理链路（每个数据集统一走这一条）:
  1. 文件探测  —— 字节数、gzip 完整性、行数
  2. 加载      —— Amazon CSV / JSONL（兼容 SNAP v1 单引号格式）、AJ 行为日志
  3. 聚合去重  —— 收敛到 (user, item, behavior) 唯一记录
  4. K-core    —— 在 (user, item) 对层面迭代过滤
  5. 行为权重  —— 评分→行为→表 4-1 的 α_b
  6. 统计      —— 规模、稀疏度、长尾、行为分布、（可选）元数据覆盖
  7. 划分      —— (user, item) 对层面 LOO 留一法 / 比例划分，并与官方划分互校
  8. 建模产物  —— 连续 ID、式(4-1) 边权重、（可选）BPR 三元组

用法:
  python prepare_data.py                       # IS/TH/OP 全部
  python prepare_data.py --categories IS       # 只处理主实验数据集
  python prepare_data.py --categories AJ       # 只处理 AJ（需 ~2GB 内存、耗时较长）
  python prepare_data.py --categories IS --with-triples   # 额外产出 BPR 三元组
  python prepare_data.py --stats-only          # 只统计不落盘
"""

import argparse
import ast
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "raw_2023"
PROCESSED_DIR = SCRIPT_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Amazon 2023 benchmark 类别（短名 -> 官方完整名）
CATEGORIES = {
    "IS": "Industrial_and_Scientific",
    "TH": "Tools_and_Home_Improvement",
    "OP": "Office_Products",
}

# AJ（Alibaba IJCAI15）不是 Amazon 数据，格式不同，走单独加载路径
AJ_DIR = SCRIPT_DIR / "raw_aj" / "data_format1"
AJ_NAME = "Alibaba_IJCAI15"

# ---- 表 4-1 行为语义权重 α_b ----
BEHAVIOR_WEIGHTS = {"buy": 3.0, "collect": 1.5, "cart": 1.2, "click": 1.0, "show": 0.1}
# 按 α 降序排列，供无需字符串映射的快速查表（category codes 直接索引）
BEHAVIOR_ORDER = ["buy", "collect", "cart", "click", "show"]
BEHAVIOR_ALPHA = np.array([BEHAVIOR_WEIGHTS[b] for b in BEHAVIOR_ORDER], dtype="float32")

# ---- 5.1.1 评分→行为推导：Amazon 无原生 cart，仅四类 ----
RATING_TO_BEHAVIOR = {5: "buy", 4: "collect", 3: "click", 2: "show", 1: "show"}

# ---- AJ 原生 action_type：0=点击 1=加购 2=成交 3=收藏（4 类原生行为）----
AJ_ACTION_TO_BEHAVIOR = {0: "click", 1: "cart", 2: "buy", 3: "collect"}

# ---- 4.1.2 式(4-1)：T=86400 秒（1 天）。λ 默认 0.001 ----
# 论文原写 λ=0.1（半衰期 6.9 天），但 IS 数据跨度 22.2 年，实测 98.9% 的边权重 <1e-6，
# 等于丢弃 99% 的图结构；λ=0.001 对应半衰期 1.9 年，与工业采购周期量级匹配，
# 且全部边得以保留。论文 4.1.2 与表 5-21 的 λ 取值需同步改为 0.001。
DEFAULT_DECAY_LAMBDA = 0.001
SECONDS_PER_DAY = 86400

# ---- 5.1.1 正负样本口径：评分≥4 为正，1~2 为硬负，未交互为软负，1:4 ----
POSITIVE_MIN_RATING = 4
HARD_NEGATIVE_MAX_RATING = 2
DEFAULT_NEG_PER_POSITIVE = 4
DEFAULT_HARD_NEG_RATIO = 0.5


def log(msg: str, level: str = "INFO"):
    """带图标的分级日志输出。"""
    prefix = {"INFO": "📊", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}.get(level, "ℹ️")
    print(f"{prefix} [{level}] {msg}")


# =====================================================================
# 一、文件探测与加载
# =====================================================================


def probe_file(filepath: Path) -> dict:
    """
    探测文件基本信息：字节数、gzip 完整性、行数。

    一次二进制遍历同时完成 gzip CRC 校验（只有读到流末尾才可能报错）与行数统计，
    避免对 GB 级文件做两遍 IO。行数按 b"\\n" 计数。
    """
    stat = {"file": filepath.name, "size_bytes": filepath.stat().st_size,
            "gzip_ok": None, "lines": 0, "parsed": 0, "failed": 0}

    n_lines = 0
    opener = gzip.open if filepath.suffix == ".gz" else open
    try:
        with opener(filepath, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                n_lines += chunk.count(b"\n")
        if filepath.suffix == ".gz":
            stat["gzip_ok"] = True
    except (OSError, EOFError) as exc:
        # gzip 截断在此抛出，正是 data_list.txt 里 TH/OP 下载失败的症状
        stat["gzip_ok"] = False
        log(f"{filepath.name} gzip 完整性校验失败: {exc}", "ERROR")

    stat["lines"] = n_lines
    return stat


def load_json_gz(filepath: Path, stat: dict | None = None) -> list[dict]:
    """
    逐行加载 JSONL(.gz)，返回字典列表。

    兼容两种格式：
      - Amazon 2023：标准 JSONL（双引号）
      - SNAP v1(2018)：meta 为 Python dict 字面量（单引号），需 ast.literal_eval 回退
    两条路径统一要求解析结果为 dict，否则计为脏行并跳过。
    """
    records, n_fallback = [], 0
    log(f"加载: {filepath.name}")

    open_fn = gzip.open if filepath.suffix == ".gz" else open
    with open_fn(filepath, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            used_fallback = False
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                used_fallback = True
                try:
                    obj = ast.literal_eval(line)
                except (ValueError, SyntaxError, MemoryError, RecursionError):
                    obj = None
            if not isinstance(obj, dict):
                if stat is not None:
                    stat["failed"] += 1
                continue
            if used_fallback:
                n_fallback += 1
            records.append(obj)

    if stat is not None:
        stat["parsed"] = len(records)
    if n_fallback:
        log(f"  {n_fallback:,} 条经 ast.literal_eval 回退解析（SNAP v1 格式）")
    if stat is not None and stat["failed"]:
        log(f"  跳过 {stat['failed']:,} 条无效记录", "WARN")
    if not records:
        raise RuntimeError(f"{filepath.name} 解析出 0 条记录，请检查文件格式")

    log(f"  读取 {len(records):,} 条记录")
    return records


def load_amazon_ratings(filepath: Path, stat: dict | None = None) -> pd.DataFrame:
    """
    加载 Amazon 2023 5-core 评分文件（CSV.gz）。

    字段 user_id, parent_asin, rating, timestamp(毫秒)；统一为
    user_id/item_id/rating/timestamp，并把毫秒时间戳转为秒。
    """
    log(f"加载评分文件: {filepath.name}")
    df = pd.read_csv(filepath, compression="gzip")

    for col in ("parent_asin", "asin"):  # 2023 版用 parent_asin，SNAP v1 用 asin
        if col in df.columns:
            df = df.rename(columns={col: "item_id"})
            break

    required = ["user_id", "item_id", "rating", "timestamp"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{filepath.name} 缺少关键列 {missing}，实际列: {list(df.columns)}")

    df = df[required].copy()
    df["rating"] = df["rating"].astype("int8")

    # 2023 版时间戳为毫秒，统一转秒（下游一律按秒处理）
    if len(df) and df["timestamp"].max() > 1e11:
        df["timestamp"] = (df["timestamp"] // 1000).astype("int64")

    if stat is not None:
        stat["parsed"] = len(df)
    log(f"  读取 {len(df):,} 条记录")
    return df


def load_aj_log(filepath: Path, stat: dict | None = None) -> pd.DataFrame:
    """
    分块加载 AJ（天猫 IJCAI15）用户行为日志，避免一次性读入 1.9GB 文本。

    字段: user_id,item_id,cat_id,seller_id,brand_id,time_stamp,action_type
    time_stamp 为 MMDD 整数（仅 2014 年 5~11 月，不跨年），补齐为 2014 年秒级时间戳。
    """
    log(f"加载 AJ 行为日志: {filepath.name}（分块读取）")
    use_cols = ["user_id", "item_id", "cat_id", "brand_id", "time_stamp", "action_type"]
    # brand_id 约 0.1% 行为空，必须用可空整型 Int32，否则 pandas 会直接抛
    # "Integer column has NA values"
    dtypes = {"user_id": "int32", "item_id": "int32", "cat_id": "Int16",
              "brand_id": "Int32", "time_stamp": "int32", "action_type": "int8"}

    parts = [chunk for chunk in
             pd.read_csv(filepath, usecols=use_cols, dtype=dtypes, chunksize=5_000_000)]
    df = pd.concat(parts, ignore_index=True)
    del parts

    # MMDD -> 2014 年秒级时间戳（不跨年，直接用年内第几天换算）
    mmdd = df.pop("time_stamp").to_numpy()
    month, day = (mmdd // 100).astype("int64"), (mmdd % 100).astype("int64")
    days_before_month = np.array([0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    base = int(pd.Timestamp("2014-01-01", tz="UTC").timestamp())
    df["timestamp"] = base + (days_before_month[month] + day) * SECONDS_PER_DAY

    if stat is not None:
        stat["parsed"] = len(df)
    log(f"  读取 {len(df):,} 条记录")
    return df


def load_meta(filepath: Path, want_items: set[str], stat: dict | None = None) -> pd.DataFrame:
    """
    流式加载物品元数据，只保留交互涉及的物品（RAG 知识库 / 4.1.4 长尾语义锚点原料）。

    2023 版主键是 parent_asin（旧版 asin），统一映射为 item_id，否则无法与评分 join。

    采用「边解析边过滤」而非先全量入内存：TH 的 meta 有 147 万行 / 解压 5.6GB，
    其中仅 ~5% 商品有交互，全量加载会占用数 GB 内存并耗时数分钟。每行只保留
    白名单字段，嵌套 list/dict 立即序列化为 JSON 字符串（否则 Arrow 会逐行编码
    成 struct，parquet 体积反超 CSV 且读取极慢）。
    """
    log(f"加载元数据: {filepath.name}（流式过滤，目标商品 {len(want_items):,} 个）")

    nest_cols = ("features", "description", "details")
    field_map = {"parent_asin": "item_id", "asin": "item_id", "store": "brand",
                 "main_category": "category", "feature": "features"}
    rows = []
    n_seen = 0
    n_failed = 0

    open_fn = gzip.open if filepath.suffix == ".gz" else open
    with open_fn(filepath, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_seen += 1
            try:
                rec = json.loads(line)
                if not isinstance(rec, dict):
                    raise ValueError("not a dict")
            except (json.JSONDecodeError, ValueError):
                try:  # SNAP v1 的 Python dict 字面量
                    rec = ast.literal_eval(line)
                    if not isinstance(rec, dict):
                        raise ValueError("not a dict")
                except (ValueError, SyntaxError, MemoryError, RecursionError):
                    n_failed += 1
                    continue

            item_id = rec.get("parent_asin") or rec.get("asin")
            if item_id not in want_items:
                continue

            row = {}
            for key, val in rec.items():
                key = field_map.get(key, key)
                if key in row:
                    continue
                if key in nest_cols and isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                elif isinstance(val, (list, dict)):
                    continue  # 非白名单嵌套字段（images/videos 等）直接丢弃
                row[key] = val
            row["item_id"] = item_id
            rows.append(row)

    if stat is not None:
        stat["parsed"] = len(rows)
        stat["failed"] = n_failed
    log(f"  扫描 {n_seen:,} 行 → 命中 {len(rows):,} 个交互商品"
        f"（跳过无效 {n_failed:,} 行）")
    if not rows:
        log("meta 中未找到任何交互商品，请检查主键字段", "WARN")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    keep = [c for c in ["item_id", "title", "brand", "category", "price",
                        "description", "features", "details"] if c in df.columns]
    if "item_id" not in keep:
        log("meta 缺少 item_id（parent_asin/asin），无法与评分对齐", "WARN")
        return pd.DataFrame()

    df = df[keep]

    # price 在 2023 版里混有 "from 24.87" 这类字符串，转数值失败者置空，
    # 否则 parquet 写出时 pyarrow 会因 object 列类型冲突报错
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        n_bad = int(df["price"].isna().sum())
        if n_bad:
            log(f"  price 非数值/缺失 {n_bad:,} 条已置空 "
                f"（有效 {1 - n_bad / len(df):.1%}）")
    return df


# =====================================================================
# 二、清洗：聚合去重 + K-core
# =====================================================================


def aggregate_behaviors(df: pd.DataFrame) -> pd.DataFrame:
    """
    把原始记录聚合为 (user_id, item_id, behavior) 唯一行。

    - Amazon：每个用户-物品对本只有一条评分，此步仅做等价去重；
    - AJ：同一对可能有多次同类点击（约 2,300 万条重复），聚合后 timestamp 取最新、
      n_records 记原始次数。不同行为（click+cart+buy）保留为独立行，
      使式(4-1)「同一对多次不同类型交互求和」得以成立。

    附带字段（AJ 的 category/brand）在对内恒定，取 first 即可。
    """
    before = len(df)
    extra = [c for c in ("category", "brand") if c in df.columns]
    agg_spec = {
        "timestamp": ("timestamp", "max"),
        "n_records": ("timestamp", "size"),
        "alpha": ("alpha", "first"),
        "is_positive": ("is_positive", "max"),          # 三元组正样本标记
        "is_hard_negative": ("is_hard_negative", "max"),  # 三元组硬负标记
    }
    if "rating" in df.columns:
        agg_spec["rating"] = ("rating", "max")
    agg = (df.groupby(["user_id", "item_id", "behavior"], observed=True)
             .agg(**agg_spec).reset_index())

    # 商品侧静态属性单独取一次，避免同一对多行为时组内取值歧义
    for col in extra:
        attr = df[["item_id", col]].drop_duplicates("item_id", keep="first")
        agg = agg.merge(attr, on="item_id", how="left")

    log(f"(user,item,behavior) 聚合: {before:,} → {len(agg):,} 行"
        f"（合并重复记录 {before - len(agg):,} 条）")
    return agg


def filter_kcore(df: pd.DataFrame, k: int = 5) -> tuple[pd.DataFrame, list[int]]:
    """
    在 (user, item) 对层面迭代 K-core 过滤，直到收敛。

    5.1.1 定义「交互次数不低于 5 的用户与商品」，计数单位是用户-物品对，
    因此多行为的同一对只计 1 次。Amazon 官方文件已 5-core，此处应为空操作。
    """
    pairs = df[["user_id", "item_id"]].drop_duplicates()
    history = [len(pairs)]
    if k <= 0:
        return df, history

    log(f"K-core 过滤 (k={k}, 计数单位=用户-物品对)...")
    for iteration in range(1, 101):
        uc = pairs["user_id"].value_counts()
        ic = pairs["item_id"].value_counts()
        kept = pairs[pairs["user_id"].isin(uc[uc >= k].index)
                     & pairs["item_id"].isin(ic[ic >= k].index)]
        history.append(len(kept))
        if len(kept) == len(pairs):
            note = "（已是 k-core，无变化）" if iteration == 1 else ""
            log(f"  收敛于第 {iteration} 轮，保留 {len(kept):,} 个用户-物品对{note}")
            return df, history
        pairs = kept
        log(f"  轮次 {iteration}: 用户-物品对 → {len(kept):,}")
    raise RuntimeError("K-core 迭代 100 轮仍未收敛")


# =====================================================================
# 三、行为推导与式(4-1) 边权重
# =====================================================================


def derive_behavior_amazon(df: pd.DataFrame) -> pd.DataFrame:
    """
    按 5.1.1 由评分推导行为类型并赋 α_b。

    rating=5→buy(3.0)，4→collect(1.5)，3→click(1.0)，1/2→show(0.1)。
    Amazon 无原生加购，故 cart(1.2) 不出现——与 docx 5.1.1 第二段说明一致。
    """
    df = df.copy()
    df["behavior"] = pd.Categorical(
        df["rating"].map(RATING_TO_BEHAVIOR), categories=BEHAVIOR_ORDER)
    df["alpha"] = BEHAVIOR_ALPHA[df["behavior"].cat.codes]
    # 5.1.1 正负口径：rating>=4 为正，1~2 为硬负；两者在聚合时按 max 合并
    df["is_positive"] = (df["rating"] >= POSITIVE_MIN_RATING).astype("int8")
    df["is_hard_negative"] = (df["rating"] <= HARD_NEGATIVE_MAX_RATING).astype("int8")
    return df


def derive_behavior_aj(df: pd.DataFrame) -> pd.DataFrame:
    """按原生 action_type 映射行为类型与 α_b（AJ 四类：click/cart/buy/collect）。"""
    df = df.copy()
    df["behavior"] = pd.Categorical(
        df["action_type"].map(AJ_ACTION_TO_BEHAVIOR), categories=BEHAVIOR_ORDER)
    if df["behavior"].isna().any():  # 未来新增 action_type 时快速失败
        bad = sorted(df.loc[df["behavior"].isna(), "action_type"].unique().tolist())
        raise ValueError(f"AJ 出现未知 action_type: {bad}")
    df["alpha"] = BEHAVIOR_ALPHA[df["behavior"].cat.codes]
    # AJ 无评分：成交(buy)视为正样本，收藏/加购亦为正；点击不算正样本（口径更严格）
    df["is_positive"] = df["behavior"].isin(["buy", "collect", "cart"]).astype("int8")
    df["is_hard_negative"] = 0  # AJ 无显式负反馈，全部负样本取自未交互软负
    return df.drop(columns=["action_type"])


def pair_last_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """计算每个 (user_id, item_id) 对的最后交互时间，作为 LOO 划分的唯一依据。"""
    return (df.groupby(["user_id", "item_id"], observed=True)["timestamp"]
              .max().rename("pair_ts").reset_index())


def compute_edge_weights(df: pd.DataFrame, lam: float = DEFAULT_DECAY_LAMBDA,
                         t_now: int | None = None) -> pd.DataFrame:
    """
    按式(4-1) 计算统一边权重 w(u,i) = Σ α_b · exp(-λ·(T_now - t)/T)。

    T_now 取数据集内最大时间戳（而非墙钟时间），保证结果可复现；T=86400 秒，
    故指数项按「天」衰减。返回 (user_idx, item_idx, weight) 及衰减诊断，
    用于检查 λ 是否与数据真实时间跨度匹配。
    """
    if t_now is None:
        t_now = int(df["timestamp"].max())

    delta_days = (t_now - df["timestamp"].to_numpy(dtype="float64")) / SECONDS_PER_DAY
    with np.errstate(under="ignore"):
        decay = np.exp(-lam * delta_days)          # 极负指数下溢为 0 属预期
    df = df.assign(_w=df["alpha"].to_numpy(dtype="float64") * decay)

    edges = (df.groupby(["user_idx", "item_idx"], observed=True)["_w"]
               .sum().rename("weight").reset_index())

    near_zero = float((edges["weight"] < 1e-6).mean())
    n_zero = int((edges["weight"] <= 0).sum())
    log(f"式(4-1) 边权重: {len(edges):,} 条边  λ={lam}  半衰期={np.log(2) / lam:.1f} 天")
    log(f"  min={edges['weight'].min():.3e}  median={edges['weight'].median():.3e}  "
        f"max={edges['weight'].max():.3e}")
    if n_zero:
        # 权重为 0 会使式(4-3) 的加权度 W_u 退化为 0，归一化时除零，必须剔除
        edges = edges[edges["weight"] > 0].reset_index(drop=True)
        log(f"  剔除 {n_zero:,} 条权重下溢为 0 的边（避免加权度除零）", "WARN")
    if near_zero > 0.5:
        log(f"  {near_zero:.1%} 的边权重 <1e-6，λ={lam} 对当前数据跨度过大，建议调小", "WARN")
    return edges


def build_bpr_triples(df: pd.DataFrame, n_neg: int = DEFAULT_NEG_PER_POSITIVE,
                      hard_ratio: float = DEFAULT_HARD_NEG_RATIO,
                      seed: int = 42) -> pd.DataFrame:
    """
    按 5.1.1 构造 BPR 三元组 (user_idx, pos_item_idx, neg_item_idx)。

    正样本：rating>=4（即 buy/collect）；硬负：该用户 rating<=2 的物品；
    软负：该用户从未交互过的随机物品。rating==3（click）不进三元组，
    但仍计入边权重与图结构。每条正样本配 n_neg 个负样本，
    其中约 hard_ratio 比例优先替换为硬负（用户无硬负池时保留软负）。
    """
    rng = np.random.default_rng(seed)
    n_items = int(df["item_idx"].max()) + 1

    pos = df.loc[df["is_positive"] == 1, ["user_idx", "item_idx"]].drop_duplicates()
    if pos.empty:
        log("无正样本，跳过三元组构造", "WARN")
        return pd.DataFrame()

    pos_u = pos["user_idx"].to_numpy(dtype="int64")
    pos_i = pos["item_idx"].to_numpy(dtype="int64")

    # 已交互 (u,i) 对的哈希键（升序），用于 O(log n) 判断随机负样本是否被观测过
    pairs = df[["user_idx", "item_idx"]].drop_duplicates()
    observed = np.sort(pairs["user_idx"].to_numpy(dtype="int64") * n_items
                       + pairs["item_idx"].to_numpy(dtype="int64"))

    # 硬负池：按 user_idx 排序后即可用 searchsorted 取每个用户的片段
    hard = (df.loc[df["is_hard_negative"] == 1, ["user_idx", "item_idx"]]
              .drop_duplicates().sort_values("user_idx"))
    hard_u = hard["user_idx"].to_numpy(dtype="int64")
    hard_i = hard["item_idx"].to_numpy(dtype="int64")

    neg_u = np.repeat(pos_u, n_neg)
    neg_p = np.repeat(pos_i, n_neg)

    # 软负：均匀随机采样，撞到已观测物品或正样本自身则重采（最多 5 轮）
    neg = rng.integers(0, n_items, size=len(neg_u), dtype=np.int64)
    for _ in range(5):
        hit = np.isin(neg_u * n_items + neg, observed) | (neg == neg_p)
        if not hit.any():
            break
        neg[hit] = rng.integers(0, n_items, size=int(hit.sum()), dtype=np.int64)

    # 硬负替换：从用户自己的 rating<=2 池中均匀抽一个
    lo = np.searchsorted(hard_u, neg_u, side="left")
    hi = np.searchsorted(hard_u, neg_u, side="right")
    pick_hard = (rng.random(len(neg_u)) < hard_ratio) & (hi > lo)
    if pick_hard.any():
        idx = lo[pick_hard] + (rng.random(int(pick_hard.sum()))
                               * (hi - lo)[pick_hard]).astype(np.int64)
        neg[pick_hard] = hard_i[np.minimum(idx, hi[pick_hard] - 1)]

    triples = pd.DataFrame({"user_idx": neg_u, "pos_item_idx": neg_p,
                            "neg_item_idx": neg})
    triples = triples[triples["neg_item_idx"] != triples["pos_item_idx"]]
    log(f"BPR 三元组: {len(triples):,} 条（正样本 {len(pos):,} × {n_neg} 负样本，"
        f"硬负实际占比 {pick_hard.mean():.1%}）")
    return triples


# =====================================================================
# 四、统计
# =====================================================================


def compute_stats(df: pd.DataFrame, name: str = "") -> dict:
    """
    计算数据集级统计：规模、稀疏度、度分布、长尾集中度、时间跨度、行为分布。

    长尾集中度用「前 20% 热门商品覆盖的交互占比」衡量，对应 4.1.4 的长尾描述；
    「交互」在表 5-1 口径下指用户-物品对，AJ 另附行为记录数。
    """
    pairs = df[["user_id", "item_id"]].drop_duplicates()
    n_pairs = len(pairs)
    n_users = int(pairs["user_id"].nunique())
    n_items = int(pairs["item_id"].nunique())
    user_deg = pairs["user_id"].value_counts()
    item_deg = pairs["item_id"].value_counts()

    # 长尾：商品按交互数降序，前 20% 商品覆盖的交互占比
    deg_sorted = np.sort(item_deg.to_numpy())[::-1]
    top20 = max(1, int(n_items * 0.2))

    stats = {
        "name": name,
        "num_pairs": n_pairs,
        "num_behavior_records": len(df),
        "num_users": n_users,
        "num_items": n_items,
        "sparsity": 1 - n_pairs / (n_users * n_items) if n_users and n_items else 0.0,
        "avg_pairs_per_user": n_pairs / n_users if n_users else 0.0,
        "median_pairs_per_user": float(user_deg.median()) if n_users else 0.0,
        "min_user_pairs": int(user_deg.min()) if n_users else 0,
        "max_user_pairs": int(user_deg.max()) if n_users else 0,
        "avg_pairs_per_item": n_pairs / n_items if n_items else 0.0,
        "min_item_pairs": int(item_deg.min()) if n_items else 0,
        "max_item_pairs": int(item_deg.max()) if n_items else 0,
        "tail_item_ratio": float((item_deg < 10).mean()) if n_items else 0.0,
        "top20pct_item_pair_share": float(deg_sorted[:top20].sum() / n_pairs),
        "timestamp_min": int(df["timestamp"].min()),
        "timestamp_max": int(df["timestamp"].max()),
    }

    # 行为分布（表 4-1 核对用：数量 / 占比 / α_b）
    if "behavior" in df.columns:
        counts = df["behavior"].value_counts()
        stats["behavior_distribution"] = {
            str(b): {"count": int(counts.get(b, 0)),
                     "pct": float(counts.get(b, 0) / len(df) * 100),
                     "alpha": BEHAVIOR_WEIGHTS[str(b)]}
            for b in counts.index
        }
    if "rating" in df.columns:
        counts = df["rating"].value_counts().sort_index()
        stats["rating_distribution"] = {str(int(k)): int(v) for k, v in counts.items()}

    return stats


def print_file_stats(file_stats: list[dict]):
    """打印文件级统计表（字节数 / gzip 完整性 / 行数 / 解析条数）。"""
    print(f"\n  文件级统计")
    print(f"  {'文件':<32}{'大小':>13}{'gzip':>7}{'行数':>14}{'解析':>14}")
    print("  " + "-" * 80)
    for s in file_stats:
        size = f"{s['size_bytes'] / 1e6:,.1f} MB"
        gz = "—" if s["gzip_ok"] is None else ("OK" if s["gzip_ok"] else "FAIL")
        print(f"  {s['file']:<32}{size:>13}{gz:>7}{s['lines']:>14,}{s['parsed']:>14,}")


def print_stats(stats: dict):
    """打印数据集级统计（覆盖 docx 表 5-1 的全部字段）。"""
    from datetime import datetime

    def fmt_ts(ts):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

    print(f"\n{'=' * 64}")
    print(f"  📊 数据集统计: {stats['name']}")
    print(f"{'=' * 64}")
    print(f"  用户数 / 商品数:      {stats['num_users']:>10,} / {stats['num_items']:,}")
    print(f"  用户-物品对数:        {stats['num_pairs']:>10,}")
    if stats["num_behavior_records"] != stats["num_pairs"]:
        print(f"  行为记录数:           {stats['num_behavior_records']:>10,}")
    print(f"  稀疏度:               {stats['sparsity']:>10.4%}")
    print(f"  平均交互/用户:        {stats['avg_pairs_per_user']:>10.2f}"
          f"（中位数 {stats['median_pairs_per_user']:.1f}）")
    print(f"  用户交互数 min/max:   {stats['min_user_pairs']:>10} / {stats['max_user_pairs']:,}")
    print(f"  商品交互数 min/max:   {stats['min_item_pairs']:>10} / {stats['max_item_pairs']:,}")
    print(f"  长尾商品(<10 交互):   {stats['tail_item_ratio']:>10.2%}")
    print(f"  前 20% 商品交互占比:  {stats['top20pct_item_pair_share']:>10.2%}")
    print(f"  时间跨度:             {fmt_ts(stats['timestamp_min'])} ~ {fmt_ts(stats['timestamp_max'])}")

    if "behavior_distribution" in stats:
        print("  行为分布:")
        for b, v in sorted(stats["behavior_distribution"].items(),
                           key=lambda kv: -kv[1]["alpha"]):
            print(f"    {b:<8} α={v['alpha']:<4} {v['count']:>13,} ({v['pct']:5.1f}%)")
    print(f"{'=' * 64}")


# =====================================================================
# 五、划分与校验
# =====================================================================


def temporal_split(df: pd.DataFrame, mode: str = "loo",
                   val_ratio: float = 0.1, test_ratio: float = 0.1) -> dict:
    """
    按时间戳做训练/验证/测试划分，划分单位是 (user, item) 对。

    以对为单位可以避免「同一对的不同行为被切到 train 和 test」造成标签泄漏；
    同一对的全部行为记录始终落在同一侧。

    mode="loo"（默认，对齐 5.1.1 留一法）：
      用户最后交互的对 → test，倒数第二个对 → valid，其余 → train。
      交互数 <3 的用户：最后一条 → test，其余 → train（无 valid）。
      时间戳并列时按 item_id 二级排序，保证划分可复现。
    mode="ratio"：按对数量比例划分（旧行为，保留作对照）。
    """
    # 对层面的最后交互时间；并列时用 item_id 打破平局
    pair_ts = pair_last_timestamp(df).sort_values(
        ["user_id", "pair_ts", "item_id"], kind="mergesort")

    labels = []
    if mode == "loo":
        log("LOO 时序划分（最后一条→test，倒数第二条→valid）...")
        for _, g in pair_ts.groupby("user_id", sort=False):
            if len(g) < 3:
                lab = ["train"] * (len(g) - 1) + ["test"]
            else:
                lab = ["train"] * (len(g) - 2) + ["valid", "test"]
            labels.extend(lab)
    else:
        log(f"比例时序划分 (val={val_ratio:.0%}, test={test_ratio:.0%})...")
        for _, g in pair_ts.groupby("user_id", sort=False):
            n = len(g)
            if n < 3:
                labels.extend(["train"] * n)
                continue
            n_test = max(1, int(n * test_ratio))
            n_val = max(1, int(n * val_ratio))
            n_train = max(1, n - n_val - n_test)
            labels.extend(["train"] * n_train + ["valid"] * n_val
                          + ["test"] * (n - n_train - n_val))

    pair_ts = pair_ts.assign(split=labels)
    result = {}
    for name, lab in (("train", "train"), ("val", "valid"), ("test", "test")):
        keys = pair_ts.loc[pair_ts["split"] == lab, ["user_id", "item_id"]]
        result[name] = df.merge(keys, on=["user_id", "item_id"], how="inner") \
            if len(keys) else df.iloc[0:0].copy()

    total_pairs = len(pair_ts)
    for name, split_df in result.items():
        n_pairs = len(split_df[["user_id", "item_id"]].drop_duplicates()) if len(split_df) else 0
        log(f"  {name}: {n_pairs:,} 对 / {len(split_df):,} 条行为记录"
            f"（{n_pairs / total_pairs * 100:.1f}% 的对）")
    return result


def verify_loo(splits: dict) -> dict:
    """
    校验 LOO 划分的三个不变量：
      1. 每位用户在 test 中恰好 1 个用户-物品对；
      2. val / test 的对都不出现在该用户的 train 中（无泄漏）。
    """
    train, val, test = splits["train"], splits["val"], splits["test"]

    def pairs_of(d):
        return set(zip(d["user_id"], d["item_id"])) if len(d) else set()

    train_pairs, val_pairs, test_pairs = pairs_of(train), pairs_of(val), pairs_of(test)
    test_per_user = Counter(u for u, _ in test_pairs)

    report = {
        "test_one_pair_per_user": all(v == 1 for v in test_per_user.values()),
        "users_in_test": len(test_per_user),
        "test_no_leak": not (test_pairs & train_pairs),
        "val_no_leak": not (val_pairs & train_pairs),
        "users_without_val": len(set(u for u, _ in train_pairs) - set(u for u, _ in val_pairs)),
    }
    ok = report["test_one_pair_per_user"] and report["test_no_leak"] and report["val_no_leak"]
    log(f"LOO 不变量校验: {'全部通过' if ok else '存在异常'}  {report}", "OK" if ok else "WARN")
    return report


def verify_against_official_loo(splits: dict, stem: str) -> dict | None:
    """
    与官方 benchmark/5core/last_out 的 test 划分互校（仅 Amazon）。

    比对 (user_id, item_id) 对的重合率；重合率接近 1 说明自建 LOO 与官方口径一致。
    差异通常来自同一时间戳并列时的 tie-break 选择。
    """
    path = RAW_DIR / "loo" / f"{stem}.test.csv.gz"
    if not path.exists():
        log("未找到官方 LOO test 文件，跳过互校", "WARN")
        return None

    official = pd.read_csv(path, compression="gzip").rename(
        columns={"parent_asin": "item_id"})
    official_pairs = set(zip(official["user_id"], official["item_id"]))
    mine_pairs = set(zip(splits["test"]["user_id"], splits["test"]["item_id"]))

    overlap = len(official_pairs & mine_pairs)
    report = {"official_test_pairs": len(official_pairs),
              "ours_test_pairs": len(mine_pairs), "overlap": overlap,
              "overlap_ratio": overlap / max(len(official_pairs), 1)}
    level = "OK" if report["overlap_ratio"] > 0.999 else "WARN"
    log(f"官方 LOO 互校: 重合 {overlap:,}/{len(official_pairs):,} "
        f"({report['overlap_ratio']:.3%})", level)
    return report


# =====================================================================
# 六、ID 编码、落盘与主流程
# =====================================================================


def encode_ids(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """把 user_id / item_id 编码为从 0 开始的连续整数，返回映射供训练侧复用。"""
    log("编码 ID 为连续整数...")
    user2idx = {u: i for i, u in enumerate(sorted(df["user_id"].unique()))}
    item2idx = {it: i for i, it in enumerate(sorted(df["item_id"].unique()))}

    df = df.copy()
    df["user_idx"] = df["user_id"].map(user2idx).astype("int32")
    df["item_idx"] = df["item_id"].map(item2idx).astype("int32")
    log(f"  用户: {len(user2idx):,}, 物品: {len(item2idx):,}")
    return df, {"user2idx": user2idx, "item2idx": item2idx}


def save_all(out_dir: Path, splits: dict, edges: pd.DataFrame,
             meta_df: pd.DataFrame | None, id_maps: dict, stats: dict,
             triples: pd.DataFrame | None, output_format: str):
    """统一落盘：划分、边权重、元数据、ID 映射、统计、三元组。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    fmts = (["csv"] if output_format in ("csv", "both") else []) + \
           (["parquet"] if output_format in ("parquet", "both") else [])

    def dump(obj: pd.DataFrame, stem_name: str):
        for fmt in fmts:
            if fmt == "csv":
                obj.to_csv(out_dir / f"{stem_name}.csv", index=False)
            else:
                obj.to_parquet(out_dir / f"{stem_name}.parquet", index=False)

    for name, split_df in splits.items():
        dump(split_df, name)
        log(f"保存 {name}: {len(split_df):,} 条行为记录")
    dump(edges, "edges")
    log(f"保存 edges: {len(edges):,} 条加权边")
    if triples is not None and not triples.empty:
        dump(triples, "triples")
        log(f"保存 triples: {len(triples):,} 条 BPR 三元组")
    if meta_df is not None and not meta_df.empty:
        dump(meta_df, "item_meta")
        log(f"保存 item_meta: {len(meta_df):,} 条")

    id_dir = out_dir / "id_maps"
    id_dir.mkdir(exist_ok=True)
    for key, mapping in id_maps.items():
        with open(id_dir / f"{key}.json", "w") as f:
            json.dump(mapping, f)

    with open(out_dir / "stats.json", "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)


def process_dataset(short_name: str, args) -> dict | None:
    """处理单个数据集的完整链路：加载 → 聚合 → k-core → 统计 → 划分 → 落盘。"""
    is_aj = short_name == "AJ"
    full_name = AJ_NAME if is_aj else CATEGORIES[short_name]
    log(f"\n处理 [{short_name}] {full_name}")
    log("=" * 55)

    file_stats = []

    # ---- 1. 加载主交互文件并推导行为 ----
    if is_aj:
        path = AJ_DIR / "user_log_format1.csv"
        if not path.exists():
            log(f"未找到 AJ 日志: {path}", "ERROR")
            return None
        stat = probe_file(path)
        df = derive_behavior_aj(load_aj_log(path, stat))
    else:
        path = RAW_DIR / f"{short_name}_5core.csv.gz"
        if not path.exists():
            log(f"未找到评分文件: {path}", "ERROR")
            return None
        stat = probe_file(path)
        df = derive_behavior_amazon(load_amazon_ratings(path, stat))
    file_stats.append(stat)
    n_raw = len(df)

    # ---- 2. 聚合去重 + K-core ----
    df = aggregate_behaviors(df)
    df, kcore_history = filter_kcore(df, args.k_core)

    # ---- 3. 元数据 ----
    meta_df = None
    if is_aj:
        # AJ 无独立元数据文件，从日志抽取 item → 类目/品牌映射
        meta_df = (df[["item_id", "category", "brand"]]
                   .drop_duplicates("item_id", keep="first"))
        log(f"AJ 物品元数据（由行为日志抽取）: {len(meta_df):,} 条")
    elif not args.skip_meta:
        meta_path = RAW_DIR / "raw" / f"{short_name}_meta.jsonl.gz"
        if meta_path.exists():
            meta_stat = probe_file(meta_path)
            # 只保留交互涉及的商品，加载时直接过滤（IS 42.7 万行中仅 2.6 万被用到）
            meta_df = load_meta(meta_path, set(df["item_id"]), meta_stat)
            file_stats.append(meta_stat)
            if not meta_df.empty:
                n_items = df["item_id"].nunique()
                covered = meta_df["item_id"].nunique()
                log(f"  元数据覆盖交互商品 {covered:,}/{n_items:,}"
                    f" = {covered / n_items:.1%}")
        else:
            log(f"未找到元数据文件: {meta_path}", "WARN")

    # ---- 4. 统计（划分前全量口径）----
    stats = compute_stats(df, name=f"{short_name}-{full_name}")
    stats.update({"raw_records": n_raw, "k_core": args.k_core,
                  "k_core_pair_history": kcore_history,
                  "meta_rows": int(len(meta_df)) if meta_df is not None else 0,
                  "file_stats": file_stats})
    print_file_stats(file_stats)
    print_stats(stats)
    if args.stats_only:
        return stats

    # ---- 5. ID 编码 → 划分 → 不变量校验 ----
    df, id_maps = encode_ids(df)
    splits = temporal_split(df, mode=args.split_mode,
                            val_ratio=args.val_ratio, test_ratio=args.test_ratio)
    stats["split_check"] = verify_loo(splits) if args.split_mode == "loo" else {}
    if not is_aj and args.split_mode == "loo":
        official = verify_against_official_loo(splits, short_name)
        if official:
            stats["official_loo_check"] = official

    # ---- 6. 式(4-1) 边权重 ----
    edges = compute_edge_weights(df, lam=args.decay_lambda)
    stats["edge_weight"] = {
        "num_edges": int(len(edges)),
        "min": float(edges["weight"].min()),
        "median": float(edges["weight"].median()),
        "max": float(edges["weight"].max()),
        "decay_lambda": args.decay_lambda,
        "t_now": int(df["timestamp"].max()),
        "near_zero_ratio": float((edges["weight"] < 1e-6).mean()),
    }

    # ---- 7. BPR 三元组（可选）----
    triples = None
    if args.with_triples:
        triples = build_bpr_triples(df, args.neg_per_positive, args.hard_neg_ratio)
        stats["bpr_triples"] = int(len(triples))

    # ---- 8. 落盘 ----
    out_dir = PROCESSED_DIR / short_name
    save_all(out_dir, splits, edges, meta_df, id_maps, stats, triples, args.output_format)
    log(f"处理完成: {out_dir}", "OK")
    return stats


def print_summary(all_stats: list[dict]):
    """打印跨数据集汇总表（用于回填 docx 表 5-1）。"""
    rows = [s for s in all_stats if s]
    if not rows:
        return
    print(f"\n{'=' * 88}")
    print("  📊 跨数据集汇总（docx 表 5-1 回填用）")
    print(f"{'=' * 88}")
    print(f"  {'数据集':<10}{'用户数':>11}{'商品数':>11}{'交互数':>13}"
          f"{'稀疏度':>11}{'均交互/用户':>13}{'行为类型':>10}")
    print("  " + "-" * 86)
    for s in rows:
        n_behav = len(s.get("behavior_distribution", {}))
        print(f"  {s['name'][:9]:<10}{s['num_users']:>11,}{s['num_items']:>11,}"
              f"{s['num_pairs']:>13,}{s['sparsity']:>11.4%}"
              f"{s['avg_pairs_per_user']:>13.2f}{n_behav:>9}类")
    print(f"{'=' * 88}\n")


def main():
    """解析命令行参数并串行处理各数据集。"""
    parser = argparse.ArgumentParser(description="Amazon 2023 / AJ 数据预处理")
    parser.add_argument("--categories", nargs="+", choices=list(CATEGORIES) + ["AJ"],
                        default=list(CATEGORIES), help="要处理的类别")
    parser.add_argument("--k-core", type=int, default=5,
                        help="K-core 阈值（默认 5，对齐 5.1.1；Amazon 官方文件已过滤，为空操作）")
    parser.add_argument("--output-format", choices=["csv", "parquet", "both"], default="both")
    parser.add_argument("--stats-only", action="store_true", help="只统计不落盘")
    parser.add_argument("--skip-meta", action="store_true", help="跳过物品元数据加载")
    parser.add_argument("--split-mode", choices=["loo", "ratio"], default="loo",
                        help="loo=留一法（默认，对齐 5.1.1），ratio=按比例")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--decay-lambda", type=float, default=DEFAULT_DECAY_LAMBDA,
                        help="式(4-1) 时间衰减率 λ（默认 0.001，半衰期 ln2/λ ≈ 1.9 年；"
                             "论文原值 0.1 在 22 年跨度上会抹掉 99%% 的边）")
    parser.add_argument("--with-triples", action="store_true", help="额外产出 BPR 三元组")
    parser.add_argument("--neg-per-positive", type=int, default=DEFAULT_NEG_PER_POSITIVE)
    parser.add_argument("--hard-neg-ratio", type=float, default=DEFAULT_HARD_NEG_RATIO)
    args = parser.parse_args()

    log("Amazon 2023 / AJ 数据预处理器")
    log(f"原始数据: {RAW_DIR}")
    log(f"输出目录: {PROCESSED_DIR}")
    log(f"K-core={args.k_core}  划分={args.split_mode}  λ={args.decay_lambda}")
    log(f"类别: {', '.join(args.categories)}")

    all_stats = [process_dataset(name, args) for name in args.categories]
    if not args.stats_only:
        print_summary(all_stats)
    log("全部处理完成!", "OK")


if __name__ == "__main__":
    main()
