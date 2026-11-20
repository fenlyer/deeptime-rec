"""G1 关口检查（W1 收口，11/21）

条件见 docs/plan/gates.md 的 G1 表。每条返回 PASS / FAIL / MANUAL：

    PASS    机械验证通过
    FAIL    机械验证未通过（关口不过）
    MANUAL  需要人看，脚本不判定（不计入失败）

用法：
    python -m gates.w1            # 终端报告
    python -m gates.w1 --json     # 机器可读
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PASS, FAIL, MANUAL = "PASS", "FAIL", "MANUAL"


def _check(name: str, fn) -> dict:
    try:
        status, detail = fn()
    except Exception as exc:  # 关口脚本本身不能崩，崩了按 FAIL 记
        status, detail = FAIL, f"{type(exc).__name__}: {exc}"
    return {"name": name, "status": status, "detail": detail}


# --------------------------------------------------------------------------- 条件
def check_checksums() -> tuple[str, str]:
    """条件 1：data/CHECKSUMS.sha256 全部 OK。"""
    manifest = REPO_ROOT / "data" / "CHECKSUMS.sha256"
    if not manifest.exists():
        return FAIL, "data/CHECKSUMS.sha256 不存在"

    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, rel = parts[0], parts[1].lstrip("*")
        expected[rel] = digest

    bad = []
    for rel, digest in expected.items():
        p = REPO_ROOT / rel
        if not p.exists():
            bad.append(f"缺失 {rel}")
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != digest:
            bad.append(f"校验失败 {rel}")
    if bad:
        return FAIL, f"{len(bad)}/{len(expected)} 项异常：" + "；".join(bad[:3])
    return PASS, f"{len(expected)} 个文件校验通过"


def check_tests() -> tuple[str, str]:
    """条件 2：pytest 全过。"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800,
    )
    tail = (proc.stdout or "").strip().splitlines()
    summary = tail[-1] if tail else "(无输出)"
    return (PASS if proc.returncode == 0 else FAIL), summary


def check_recbole_env() -> tuple[str, str]:
    """条件 3：recbole.yml 存在，且冒烟产物存在。"""
    lock = REPO_ROOT / "environment" / "recbole.yml"
    smoke = REPO_ROOT / "results" / "_smoke"
    if not lock.exists():
        return FAIL, "environment/recbole.yml 不存在"
    if not smoke.is_dir() or not any(smoke.rglob("*.json")):
        return FAIL, "results/_smoke/ 下没有冒烟产物"
    return PASS, "recbole.yml 存在，冒烟产物存在"


def check_number_pipeline() -> tuple[str, str]:
    """条件 4：make tables 可运行并产出 numbers.json。"""
    script = REPO_ROOT / "scripts" / "make_tables.py"
    out = REPO_ROOT / "thesis" / "generated" / "numbers.json"
    if not script.exists():
        return FAIL, "scripts/make_tables.py 不存在"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        return FAIL, (proc.stderr or proc.stdout).strip().splitlines()[-1:]
    if not out.exists():
        return FAIL, "numbers.json 未生成"
    data = json.loads(out.read_text(encoding="utf8"))
    return PASS, f"numbers.json 含 {len(data)} 个数字"


def check_profile_figures() -> tuple[str, str]:
    """条件 5：IS 画像图至少 5 张。"""
    fig_dir = REPO_ROOT / "figures" / "profile"
    if not fig_dir.is_dir():
        return FAIL, "figures/profile/ 不存在"
    svgs = sorted(fig_dir.glob("IS_*.svg"))
    if len(svgs) < 5:
        return FAIL, f"仅 {len(svgs)} 张（需 ≥5）"
    return PASS, f"{len(svgs)} 张：{', '.join(p.stem for p in svgs[:6])}"


def check_recall_baseline() -> tuple[str, str]:
    """条件 6：至少一个召回基线 run 有 metrics.json。"""
    base = REPO_ROOT / "results" / "ch3_recall" / "baselines"
    if not base.is_dir():
        return FAIL, "results/ch3_recall/baselines/ 不存在"
    runs = sorted(base.glob("*/seed*/metrics.json"))
    if not runs:
        return FAIL, "没有 seed*/metrics.json"
    return PASS, f"{len(runs)} 个 run（例：{runs[0].relative_to(REPO_ROOT)}）"


def check_prototype_inventory() -> tuple[str, str]:
    """条件 7：原型现状表存在且有内容。"""
    p = REPO_ROOT / "docs" / "prototype_inventory.md"
    if not p.exists():
        return FAIL, "docs/prototype_inventory.md 不存在"
    text = p.read_text(encoding="utf8").strip()
    if len(text) < 200:
        return FAIL, f"内容过短（{len(text)} 字符）"
    return PASS, f"{len(text)} 字符"


CHECKS = [
    ("G1-1 冻结数据可校验", check_checksums),
    ("G1-2 统一评估可复现", check_tests),
    ("G1-3 RecBole 环境可复现", check_recbole_env),
    ("G1-4 数字管线可运行", check_number_pipeline),
    ("G1-5 数据画像图就绪", check_profile_figures),
    ("G1-6 召回基线至少 1 个", check_recall_baseline),
    ("G1-7 原型现状可查", check_prototype_inventory),
]


# --------------------------------------------------------------------------- 入口
def run() -> list[dict]:
    return [_check(name, fn) for name, fn in CHECKS]


def main() -> int:
    ap = argparse.ArgumentParser(description="G1 关口检查")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    results = run()
    failed = [r for r in results if r["status"] == FAIL]

    if args.json:
        print(json.dumps({"gate": "G1", "results": results, "passed": not failed},
                         ensure_ascii=False, indent=2))
    else:
        print("G1 关口检查（W1 收口）")
        print("=" * 60)
        for r in results:
            mark = {"PASS": "✅", "FAIL": "❌", "MANUAL": "◻"}[r["status"]]
            print(f"{mark} {r['name']}")
            print(f"    {r['detail']}")
        print("=" * 60)
        print("通过" if not failed else f"未通过：{len(failed)} 项")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
