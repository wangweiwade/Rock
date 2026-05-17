"""使用 matplotlib 绘制齿轮箱外形/安装尺寸示意图。

依赖 data/dimensions.csv 中的关键尺寸字段(L/W/H/h/a/A1/B1/d2/n1/n2/s)。
若该型号在 dimensions.csv 中无记录,函数返回带"尺寸数据未录入"提示的占位图。
"""

from __future__ import annotations
from io import BytesIO
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from .models import Gearbox

# 中文字体在 streamlit cloud 上可能缺失;使用 DejaVu Sans + 标签英文 + 数值
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def render_drawing(gearbox: Gearbox, type_code: str) -> bytes:
    """返回 PNG 字节流。"""
    dims = gearbox.dims
    fig, (ax_front, ax_top) = plt.subplots(1, 2, figsize=(12, 6))

    if not dims or dims.get("L", 0) == 0:
        for ax in (ax_front, ax_top):
            ax.text(
                0.5, 0.5,
                f"Outline drawing for {type_code}\n(dimension data not yet loaded)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=11, color="gray",
            )
            ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    L = dims.get("L", 1000)
    W = dims.get("W", 500)
    H = dims.get("H", 700)
    h = dims.get("h", 350)
    A1 = dims.get("A1", L * 0.3)
    B1 = dims.get("B1", W * 0.8)
    n1 = dims.get("n1", L * 0.7)
    n2 = dims.get("n2", W * 0.3)
    d2 = dims.get("d2", 150)
    s = dims.get("s", 30)

    # --- 主视图:长 L × 高 H,中心高 h,输出轴在右侧 ---
    ax_front.add_patch(patches.Rectangle((0, 0), L, H, fill=False, lw=2, edgecolor="#1f4e79"))
    ax_front.axhline(h, color="#bbb", lw=0.7, ls="--")
    ax_front.add_patch(patches.Rectangle((L, h - d2 / 2), d2 * 1.8, d2, fill=False, lw=1.5,
                                          edgecolor="#1f4e79"))
    # 输入轴(左)
    ax_front.add_patch(patches.Rectangle((-d2 * 1.2, h + H * 0.15 - d2 * 0.3),
                                          d2 * 1.2, d2 * 0.6,
                                          fill=False, lw=1.5, edgecolor="#1f4e79"))
    ax_front.annotate("", xy=(L + d2 * 1.8 + 80, h), xytext=(L + d2 * 1.8, h),
                      arrowprops=dict(arrowstyle="-|>", color="black", lw=1))
    ax_front.text(L + d2 * 1.8 + 90, h, "Output shaft", va="center", fontsize=9)
    # 尺寸标注
    ax_front.annotate("", xy=(0, -H * 0.13), xytext=(L, -H * 0.13),
                      arrowprops=dict(arrowstyle="<->", color="black"))
    ax_front.text(L / 2, -H * 0.18, f"L = {L:.0f} mm", ha="center", fontsize=10)
    ax_front.annotate("", xy=(-W * 0.18, 0), xytext=(-W * 0.18, H),
                      arrowprops=dict(arrowstyle="<->", color="black"))
    ax_front.text(-W * 0.25, H / 2, f"H = {H:.0f}", rotation=90, va="center", fontsize=10)
    ax_front.text(L / 2, h + 12, f"h = {h:.0f}", ha="center", fontsize=9, color="#666")
    ax_front.set_xlim(-W * 0.4, L + d2 * 4)
    ax_front.set_ylim(-H * 0.3, H * 1.2)
    ax_front.set_aspect("equal")
    ax_front.set_title(f"Front view — {type_code}", fontsize=12)
    ax_front.set_xticks([]); ax_front.set_yticks([])

    # --- 俯视图:长 L × 宽 W,标地脚孔阵列 ---
    ax_top.add_patch(patches.Rectangle((0, 0), L, W, fill=False, lw=2, edgecolor="#1f4e79"))
    # 4 个地脚孔(arranged at corners of B1×A1 inset)
    margin_x = (L - n1) / 2
    margin_y = (W - n2) / 2
    for cx, cy in [
        (margin_x, margin_y),
        (margin_x + n1, margin_y),
        (margin_x, margin_y + n2),
        (margin_x + n1, margin_y + n2),
    ]:
        ax_top.add_patch(patches.Circle((cx, cy), s / 2, fill=False, lw=1.2, edgecolor="#c66"))
    # n1 标注
    ax_top.annotate("", xy=(margin_x, -W * 0.15), xytext=(margin_x + n1, -W * 0.15),
                    arrowprops=dict(arrowstyle="<->", color="#c66"))
    ax_top.text(margin_x + n1 / 2, -W * 0.22, f"n1 = {n1:.0f}", ha="center", fontsize=9, color="#c66")
    # n2 标注
    ax_top.annotate("", xy=(-L * 0.1, margin_y), xytext=(-L * 0.1, margin_y + n2),
                    arrowprops=dict(arrowstyle="<->", color="#c66"))
    ax_top.text(-L * 0.16, margin_y + n2 / 2, f"n2 = {n2:.0f}",
                rotation=90, va="center", fontsize=9, color="#c66")
    # L、W 标注
    ax_top.annotate("", xy=(0, W + W * 0.1), xytext=(L, W + W * 0.1),
                    arrowprops=dict(arrowstyle="<->", color="black"))
    ax_top.text(L / 2, W + W * 0.15, f"L = {L:.0f}", ha="center", fontsize=10)
    ax_top.annotate("", xy=(L + L * 0.05, 0), xytext=(L + L * 0.05, W),
                    arrowprops=dict(arrowstyle="<->", color="black"))
    ax_top.text(L + L * 0.10, W / 2, f"W = {W:.0f}", rotation=90, va="center", fontsize=10)
    # 输出轴
    ax_top.add_patch(patches.Rectangle((L, W / 2 - d2 / 2), d2 * 1.8, d2,
                                        fill=False, lw=1.5, edgecolor="#1f4e79"))
    ax_top.set_xlim(-L * 0.25, L + L * 0.25)
    ax_top.set_ylim(-W * 0.35, W * 1.3)
    ax_top.set_aspect("equal")
    ax_top.set_title("Top view — bolt hole pattern", fontsize=12)
    ax_top.set_xticks([]); ax_top.set_yticks([])

    fig.suptitle(f"Rock Gearbox  {type_code}",
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
