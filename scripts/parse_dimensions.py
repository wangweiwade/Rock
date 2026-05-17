"""解析 Rock.pdf 尺寸表(p.25/27/29/31/33/35/37/39/41),输出结构化 CSV。

每个尺寸页有 3-4 个子表,均为"机座号作为行 / 字母作为列"。
通过 pdfminer 取每个文本块的 (x, y),对同一 y 上的所有 token 按 x 邻近匹配到字母列。

输出:
  data/dimensions_full.csv
  每行 = (series_code, size, dim_letter, value)
  例:
    RKB3, 12, a, "1260"
    RKB3, 12, A1, "370"
    RKB3, 12, d2, "180"
    RKB3, 12, weight_kg, "1340"
"""

from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "docs" / "Rock.pdf"
OUT = ROOT / "data" / "dimensions_full.csv"


# (page_1based, series_code, sub_type_label, [sizes...])
DIMENSION_PAGES = [
    # RKH1SH 3-18 (single sub-type)
    (25, "RKH1", "RKH1SH", list(range(3, 18))),  # sizes 3-17 per p.24/25 (size 18 not in table)
    # RKH2 split into two pages
    (27, "RKH2", "RKH2_H", list(range(3, 13))),
    (29, "RKH2", "RKH2_H", list(range(13, 19))),
    # RKH3
    (31, "RKH3", "RKH3_H", list(range(5, 13))),
    (33, "RKH3", "RKH3_H", list(range(13, 19))),
    # RKB2
    (35, "RKB2", "RKB2_H", list(range(4, 13))),
    (37, "RKB2", "RKB2_H", list(range(13, 19))),
    # RKB3
    (39, "RKB3", "RKB3_H", list(range(4, 13))),
    (41, "RKB3", "RKB3_H", list(range(13, 19))),
]


def collect_items(page_idx_0: int):
    pages = list(extract_pages(str(PDF), page_numbers=[page_idx_0]))
    items = []
    for el in pages[0]:
        if isinstance(el, LTTextContainer):
            for line in el:
                if isinstance(line, LTTextLine):
                    t = line.get_text().strip()
                    if t:
                        items.append({
                            "text": t,
                            "x": (line.x0 + line.x1) / 2,
                            "x0": line.x0,
                            "y": line.y0,
                        })
    return items


def rows_by_y(items):
    by_y = defaultdict(list)
    for it in items:
        by_y[round(it["y"])].append(it)
    return by_y


def find_header_rows(items, expected_letters: set[str]):
    """找标题行: 在某个 y 上同时出现至少 4 个字母标签."""
    by_y = rows_by_y(items)
    headers = []
    for y, row in by_y.items():
        labels = [it for it in row if it["text"] in expected_letters]
        if len(labels) >= 3:
            headers.append((y, sorted(labels, key=lambda x: x["x"])))
    return headers


# 各表期望出现的字母集合(用于识别标题行)
MAIN_LETTERS_TOP = {"a", "A1", "A2", "A3", "A4", "b", "B1", "B2", "B3",
                    "c", "c1", "d6", "D5", "e", "e2", "e3", "E", "g"}
MAIN_LETTERS_BOT = {"G6", "h", "h1", "h2", "h5", "H", "m1", "m2", "m3",
                    "n1", "n2", "n3", "n4", "s"}
SHAFT_LETTERS = {"d2", "G2", "l2", "D2", "G4", "D3", "D4", "G5"}
WEIGHT_LABEL = {"(kg)"}


def parse_subtable(items, expected_letters: set[str], sizes: list[int]):
    """识别一个子表:
       1. 找标题行(包含 ≥3 个字母)
       2. 从标题行下方往下找 size 数据行(最左 x 是 size 数字)
       3. 每行的其他 token 按 x 距离匹配到字母列
    """
    headers = find_header_rows(items, expected_letters)
    out: dict[int, dict[str, str]] = defaultdict(dict)
    for header_y, label_items in headers:
        # 字母列的 x 坐标
        cols = {it["text"]: it["x"] for it in label_items}
        col_xs = sorted(cols.values())
        col_by_x = {it["x"]: it["text"] for it in label_items}
        # 找所有 y < header_y 且文本是 size 的 token
        for it in items:
            if it["y"] >= header_y - 4 or it["y"] < header_y - 200:
                continue
            try:
                size_val = int(it["text"])
            except ValueError:
                continue
            if size_val not in sizes or it["x0"] > 70:  # size 在最左列
                continue
            row_y = it["y"]
            # 取与 row_y 接近 (±2) 的同行 token
            row_items = [t for t in items
                         if abs(t["y"] - row_y) <= 2 and t["x"] > it["x"] + 5]
            # 把每个 token 按最近列归属
            for ri in row_items:
                # 找最近的 col_x
                best_x, best_d = None, 999
                for cx in col_xs:
                    d = abs(ri["x"] - cx)
                    if d < best_d:
                        best_d = d; best_x = cx
                if best_x is not None and best_d <= 30:
                    label = col_by_x[best_x]
                    out[size_val][label] = ri["text"]
    return out


def parse_page(page_1based: int, sizes: list[int]):
    items = collect_items(page_1based - 1)
    result: dict[int, dict[str, str]] = defaultdict(dict)
    # 主体 top (a, A1, etc.)
    for sz, d in parse_subtable(items, MAIN_LETTERS_TOP, sizes).items():
        result[sz].update(d)
    # 主体 bot (G6, h, etc.)
    for sz, d in parse_subtable(items, MAIN_LETTERS_BOT, sizes).items():
        result[sz].update(d)
    # 输出轴
    for sz, d in parse_subtable(items, SHAFT_LETTERS, sizes).items():
        result[sz].update(d)
    return result


def main():
    all_dims: list[dict] = []
    for page, series_code, _sub, sizes in DIMENSION_PAGES:
        print(f"  parsing p.{page} {series_code} sizes {sizes[0]}-{sizes[-1]}...")
        result = parse_page(page, sizes)
        for size, dims in result.items():
            for letter, value in dims.items():
                all_dims.append({
                    "series_code": series_code,
                    "size": size,
                    "dim_letter": letter,
                    "value": value,
                })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["series_code", "size", "dim_letter", "value"])
        w.writeheader()
        for row in all_dims:
            w.writerow(row)
    # 统计
    sizes_per_series = defaultdict(set)
    for r in all_dims:
        sizes_per_series[r["series_code"]].add(int(r["size"]))
    print(f"\nTotal entries: {len(all_dims)}")
    for sc, sizes in sorted(sizes_per_series.items()):
        print(f"  {sc}: {len(sizes)} sizes × ~{len(all_dims)//len(sizes_per_series)//len(sizes)} dims")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
