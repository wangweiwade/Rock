"""提取 Rock.pdf 中的官方外形/安装尺寸图(每个机型一页),按需渲染成 PNG。

PDF 外形图分布(对照 Rock.pdf 目录页 24-41):
  Series  Sub-type                          Size range  Drawing page
  RKH1    SH                                3-18        24
  RKH2    SH / HH / DH                      3-12        26
  RKH2    SH / HH / HM / DH / DM            13-18       28   (新增 M 形式)
  RKH3    SH / HH / DH                      5-12        30
  RKH3    SH / HH / HM / DH / DM            13-18       32
  RKB2    SH / HH / DH                      4-12        34
  RKB2    SH / HH / HM / DH / DM            13-18       36
  RKB3    SH / HH / DH                      4-12        38
  RKB3    SH / HH / HM / DH / DM            13-18       40

约束:M 形式(无地脚)仅 size ≥ 13 才有产品。
"""

from __future__ import annotations
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium

from .models import Gearbox

PDF_PATH = Path(__file__).resolve().parent.parent / "docs" / "Rock.pdf"


# (series_code, size_range_lo, size_range_hi) -> 1-indexed PDF page
_DRAWING_PAGES = {
    # RKH1
    ("RKH1", 3, 18):  24,
    # RKH2
    ("RKH2", 3, 12):  26,
    ("RKH2", 13, 18): 28,
    # RKH3
    ("RKH3", 5, 12):  30,
    ("RKH3", 13, 18): 32,
    # RKB2
    ("RKB2", 4, 12):  34,
    ("RKB2", 13, 18): 36,
    # RKB3
    ("RKB3", 4, 12):  38,
    ("RKB3", 13, 18): 40,
}


def get_drawing_page(series_code: str, size: int) -> int | None:
    """返回该型号外形图所在的 1-indexed PDF 页号;若无匹配返回 None。"""
    for (sc, lo, hi), page in _DRAWING_PAGES.items():
        if sc == series_code and lo <= size <= hi:
            return page
    return None


def get_dimensions_page(series_code: str, size: int) -> int | None:
    """尺寸数据表页(外形图的下一页)。"""
    p = get_drawing_page(series_code, size)
    return p + 1 if p else None


def mounting_available(series_code: str, size: int, mounting: str) -> tuple[bool, str]:
    """M 形式(无地脚)只在 size ≥ 13 才有产品。返回 (ok, message)。"""
    if mounting == "M" and size < 13:
        return False, (
            f"❌ {series_code} 机座号 {size}(< 13)无 M 形式(卧式无地脚)产品。"
            f"M 形式仅 size 13-18 提供,小尺寸请选 H 形式(卧式带地脚)。"
        )
    return True, ""


@lru_cache(maxsize=20)
def _render_page(page_idx_0based: int, scale: float = 2.0) -> bytes:
    """渲染指定页为 PNG 字节。LRU 缓存避免重复渲染。"""
    pdf = pdfium.PdfDocument(str(PDF_PATH))
    page = pdf[page_idx_0based]
    bitmap = page.render(scale=scale)
    pil_img = bitmap.to_pil()
    buf = BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_drawing(gearbox: Gearbox, type_code: str) -> bytes:
    """返回该型号外形图的 PNG 字节。"""
    page = get_drawing_page(gearbox.series_code, gearbox.size)
    if page is None:
        # 无匹配时返回提示占位图
        return _placeholder(type_code, "该机型外形图未在手册中找到")
    return _render_page(page - 1, scale=2.0)


def render_dimensions_table(gearbox: Gearbox) -> bytes | None:
    """返回该型号的尺寸数据表页 PNG 字节(外形图后一页)。"""
    page = get_dimensions_page(gearbox.series_code, gearbox.size)
    if page is None:
        return None
    return _render_page(page - 1, scale=2.0)


def _placeholder(type_code: str, msg: str) -> bytes:
    """无 PDF 匹配时的占位图。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 380), f"{type_code}", fill="black")
    d.text((40, 420), msg, fill="gray")
    d.rectangle((20, 20, 1180, 780), outline="lightgray", width=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
