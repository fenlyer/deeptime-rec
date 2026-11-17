"""统一的绘图样式（S0-b）

论文所有实验图共用本模块，保证字体、字号、线宽、配色一致。

约定（来自执行计划附录 E）：
    - 中文宋体、西文 Times New Roman，字号 10.5pt
    - 同时导出 SVG 与 600dpi PNG
    - 单栏宽 8.5cm，双栏宽 17cm（由调用方指定）

用法：
    from plot_style import apply_style, save_fig
    apply_style()
    fig, ax = plt.subplots(figsize=(W_SINGLE, 6))
    ...
    save_fig(fig, "figures/profile/rating_dist")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无界面后端，服务器与本地行为一致

import matplotlib.pyplot as plt

# 画布尺寸（英寸）：cm / 2.54
CM = 1 / 2.54
W_SINGLE = 8.5 * CM   # 单栏
W_DOUBLE = 17.0 * CM  # 双栏

_FONT_SIZE = 10.5
_CN_FONT = "Songti SC"        # macOS 自带宋体；Linux 可换 Noto Serif CJK SC
_EN_FONT = "Times New Roman"

# 配色：低饱和、印刷友好的离散色板
PALETTE = [
    "#4C6EF5",  # 蓝
    "#F08C00",  # 橙
    "#2F9E44",  # 绿
    "#C92A2A",  # 红
    "#7048E8",  # 紫
    "#0C8599",  # 青
]


def apply_style() -> None:
    """把论文样式写入 matplotlib 全局 rcParams。幂等，可重复调用。

    中文字体策略：
        - 西文优先，中文字符 fallback 到宋体
        - matplotlib 不会跨 family 自动 fallback，所以把中文字体放在 serif 列表最前，
          靠 font.family=serif 让所有字符统一走 serif 通道
        - 如果系统里宋体不可用，脚本会直接抛错而不是生成一堆乱码 PDF
    """
    import matplotlib.font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    if _CN_FONT not in available:
        candidates = ["Noto Serif CJK SC", "Source Han Serif SC", "STSong", "SimSun"]
        found = [c for c in candidates if c in available]
        if not found:
            raise RuntimeError(
                f"未找到宋体字体（{_CN_FONT} 或备选 {candidates}）。"
                "请安装中文字体或修改 _CN_FONT 常量。"
            )
        # 替换为系统实际存在的宋体
        globals()["_CN_FONT"] = found[0]

    plt.rcParams.update(
        {
            "font.family": "serif",
            # 列表顺序：中文字体在前，保证中文字符能命中；西文字体紧随其后
            "font.serif": [_CN_FONT, _EN_FONT],
            "font.size": _FONT_SIZE,
            "axes.titlesize": _FONT_SIZE,
            "axes.labelsize": _FONT_SIZE,
            "xtick.labelsize": _FONT_SIZE - 1,
            "ytick.labelsize": _FONT_SIZE - 1,
            "legend.fontsize": _FONT_SIZE - 1,
            "axes.unicode_minus": False,  # 负号用 ASCII，避免缺字形
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "lines.linewidth": 1.2,
            "lines.markersize": 4,
            "legend.frameon": False,
            "figure.dpi": 120,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        }
    )
    # 清掉字体缓存里的 fallback 标记，确保新设置立即生效
    fm._load_fontmanager(try_read_cache=False)


def save_fig(fig, path_no_ext: str | Path, dpi: int = 600) -> list[Path]:
    """同时导出 SVG 与 600dpi PNG。

    参数
    ----
    fig : matplotlib.figure.Figure
    path_no_ext : 不含扩展名的路径，父目录不存在时自动创建
    dpi : PNG 分辨率，默认 600

    返回
    ----
    实际写出的文件路径列表
    """
    base = Path(path_no_ext)
    base.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("svg", "png"):
        out = base.with_suffix(f".{ext}")
        fig.savefig(out, dpi=dpi, format=ext)
        written.append(out)
    return written