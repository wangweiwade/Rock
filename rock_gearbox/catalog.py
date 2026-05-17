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
