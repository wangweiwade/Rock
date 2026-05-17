"""目录数据加载与查询。"""

from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import csv

from .models import Gearbox


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# 标准 R20 公称速比序列(完整目录覆盖范围)
STANDARD_RATIOS = [
    1.25, 1.4, 1.6, 1.8, 2.0, 2.24, 2.5, 2.8, 3.15, 3.55,
    4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 9.0, 10.0, 11.2,
    12.5, 14.0, 16.0, 18.0, 20.0, 22.4, 25.0, 28.0, 31.5, 35.5,
    40.0, 45.0, 50.0, 56.0, 63.0, 71.0, 80.0, 90.0, 100.0, 112.0,
]


def nearest_standard_ratio(i_required: float) -> float:
    """从 R20 标准系列中选最接近的 i_N。"""
    return min(STANDARD_RATIOS, key=lambda x: abs(x - i_required))


@dataclass(frozen=True)
class CatalogEntry:
    family: str
    stage: int
    series_code: str
    size: int
    ratio_nominal: float
    ratio_actual: float | None
    t2n_nm: float
    p_gn_kw: float | None
    p_gf_kw: float | None
    p_gc_kw: float | None
    p_gfc_kw: float | None

    def to_gearbox(self, dims: dict[str, float] | None = None) -> Gearbox:
        return Gearbox(
            family=self.family,
            stage=self.stage,
            series_code=self.series_code,
            size=self.size,
            ratio_nominal=self.ratio_nominal,
            ratio_actual=self.ratio_actual or self.ratio_nominal,
            t2n_nm=self.t2n_nm,
            p_gn_kw=self.p_gn_kw,
            p_gf_kw=self.p_gf_kw,
            p_gc_kw=self.p_gc_kw,
            p_gfc_kw=self.p_gfc_kw,
            dims=dims or {},
        )


@lru_cache(maxsize=1)
def load_entries() -> list[CatalogEntry]:
    """加载 ratio_torque.csv + thermal_power.csv 合并成扁平条目列表。"""
    rt_rows: list[dict] = []
    with open(DATA_DIR / "ratio_torque.csv", encoding="utf-8") as f:
        rt_rows = list(csv.DictReader(f))

    # 热功率以 (family, size, ratio_nominal) 为键
    thermal: dict[tuple[str, int, float], dict] = {}
    with open(DATA_DIR / "thermal_power.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["family"], int(r["size"]), float(r["ratio_nominal"]))
            thermal[key] = r

    entries: list[CatalogEntry] = []
    for r in rt_rows:
        family = r["family"]
        size = int(r["size"])
        ratio = float(r["ratio_nominal"])
        ratio_actual_raw = r["ratio_actual"]
        ratio_actual = float(ratio_actual_raw) if ratio_actual_raw else None
        t_row = thermal.get((family, size, ratio))

        def _opt(key: str) -> float | None:
            if t_row is None:
                return None
            v = t_row.get(key, "")
            return float(v) if v else None

        entries.append(
            CatalogEntry(
                family=family,
                stage=int(r["stage"]),
                series_code=r["series_code"],
                size=size,
                ratio_nominal=ratio,
                ratio_actual=ratio_actual,
                t2n_nm=float(r["t2n_nm"]),
                p_gn_kw=_opt("p_gn_kw"),
                p_gf_kw=_opt("p_gf_kw"),
                p_gc_kw=_opt("p_gc_kw"),
                p_gfc_kw=_opt("p_gfc_kw"),
            )
        )
    return entries


@lru_cache(maxsize=1)
def load_dimensions() -> dict[tuple[str, int], dict[str, float]]:
    """加载 dimensions.csv,键为 (series_code, size)。"""
    out: dict[tuple[str, int], dict[str, float]] = {}
    with open(DATA_DIR / "dimensions.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["series_code"], int(r["size"]))
            dims = {}
            for k, v in r.items():
                if k in ("series_code", "size"):
                    continue
                try:
                    dims[k] = float(v) if v else 0.0
                except ValueError:
                    pass
            out[key] = dims
    return out


@lru_cache(maxsize=1)
def load_dimensions_full() -> dict[tuple[str, int], dict[str, str]]:
    """加载 dimensions_full.csv (按 PDF 字母提取),键为 (series_code, size)。

    返回 {(series, size): {dim_letter: value_str}},值保持字符串以容纳"30±1"、"24 H9"等。
    """
    out: dict[tuple[str, int], dict[str, str]] = {}
    path = DATA_DIR / "dimensions_full.csv"
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["series_code"], int(r["size"]))
            out.setdefault(key, {})[r["dim_letter"]] = r["value"]
    return out


def get_full_dimensions(series_code: str, size: int) -> dict[str, str]:
    """返回该型号所有字母维度,如 {'a': '1260', 'A1': '370', 'd2': '180', ...}。"""
    return load_dimensions_full().get((series_code, size), {})


# 字母 → 中文描述(对照 Rock.pdf 外形图中的尺寸标注)
DIM_DESCRIPTIONS: dict[str, str] = {
    # 长度方向
    "a":  "外形总长",
    "A1": "前安装面到中心距",
    "A2": "后安装面到中心距",
    "A3": "辅助安装面距",
    "A4": "M 端安装面距",
    # 宽度方向
    "b":  "外形总宽",
    "B1": "地脚孔宽度间距",
    "B2": "辅助孔间距",
    "B3": "底座宽度",
    # 高度方向
    "H":  "外形总高",
    "h":  "中心高(轴中心到底)",
    "h5": "地脚到中心垂距",
    "h1": "M 形式中心高",
    "h2": "M 形式辅助高",
    # 倒角与孔
    "c":  "地脚倒角",
    "c1": "地脚螺栓 (M×L)",
    "d6": "地脚螺栓孔直径",
    "D5": "中心孔配合",
    "s":  "地脚孔直径(穿透)",
    # 端面距
    "e":  "输出轴中心到地脚",
    "e2": "辅助端面距",
    "e3": "前端面到法兰",
    "E":  "输入轴中心到法兰",
    # m/n 序列(轴向位置 / 地脚孔间距)
    "m1": "M1 端轴向距",
    "m2": "M2 端轴向距",
    "m3": "M3 端轴向距",
    "n1": "地脚孔纵向中心距 1",
    "n2": "地脚孔纵向中心距 2",
    "n3": "地脚孔横向中心距 3",
    "n4": "地脚孔横向中心距 4",
    "g":  "输出轴端面到地脚距",
    "G1": "输入轴端面到法兰",
    "G2": "输出轴端面距",
    "G3": "输入轴定位距",
    "G4": "空心轴轴向距",
    "G5": "收缩盘端轴向距",
    "G6": "外形总长(M 形式)",
    # 轴端
    "d1": "输入轴直径",
    "l1": "输入轴长",
    "l3": "输入轴键槽长",
    "d2": "输出轴直径(实心)",
    "G2": "输出轴端面距",
    "l2": "输出轴长(实心)",
    "D2": "输出空心轴内径",
    "D3": "收缩盘空心轴内径",
    "D4": "收缩盘外径",
}


DIM_GROUPS: dict[str, list[str]] = {
    "主体外形 (Body envelope)": ["a", "b", "H", "h", "h5", "h1", "h2", "G6"],
    "安装与连接 (Mounting)":   ["A1", "A2", "A3", "A4", "B1", "B2", "B3",
                              "n1", "n2", "n3", "n4", "s", "d6", "c", "c1"],
    "端面距 (End faces)":     ["e", "e2", "e3", "E", "g", "m1", "m2", "m3"],
    "输入轴 (Input shaft)":    ["d1", "l1", "l3", "G1", "G3"],
    "输出轴 (Output shaft)":   ["d2", "G2", "l2", "D2", "D3", "D4", "G4", "G5", "D5"],
}


def find_candidates(
    family: str,
    ratio_nominal: float,
) -> list[CatalogEntry]:
    """筛选 (family, ratio_nominal) 匹配的所有候选,按机座号升序。"""
    entries = load_entries()
    if family == "auto":
        candidates = [e for e in entries if e.ratio_nominal == ratio_nominal]
    else:
        candidates = [e for e in entries if e.family == family and e.ratio_nominal == ratio_nominal]
    return sorted(candidates, key=lambda e: (e.size, e.stage))


def get_dimensions(series_code: str, size: int) -> dict[str, float]:
    return load_dimensions().get((series_code, size), {})
