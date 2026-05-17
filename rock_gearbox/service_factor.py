"""服务系数 f1, f2, f3, f4, f5, f8 查表(对照 Rock.pdf 第 10-11 页)。"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import csv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _hour_band(hours_per_day: float) -> str:
    if hours_per_day <= 0.5:
        return "le_0_5"
    if hours_per_day <= 10:
        return "le_10"
    return "gt_10"


def _starts_band(starts_per_hour: int) -> str:
    if starts_per_hour <= 5:
        return "le_5"
    if starts_per_hour <= 30:
        return "6_to_30"
    if starts_per_hour <= 100:
        return "31_to_100"
    return "gt_100"


@lru_cache(maxsize=1)
def _f1_table() -> dict[str, dict]:
    out = {}
    with open(DATA_DIR / "service_factor_f1.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["application_key"]] = r
    return out


@lru_cache(maxsize=1)
def _f2_table() -> dict[str, float]:
    out = {}
    with open(DATA_DIR / "service_factor_f2.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["prime_mover"]] = float(r["f2"])
    return out


@lru_cache(maxsize=1)
def _f3_table() -> dict[str, dict[str, float]]:
    out = {}
    with open(DATA_DIR / "service_factor_f3.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["starts_band"]] = {
                "unidirectional": float(r["f3_unidirectional"]),
                "alternating": float(r["f3_alternating"]),
            }
    return out


@lru_cache(maxsize=1)
def _f4_table() -> dict[tuple[int, int], float]:
    out = {}
    with open(DATA_DIR / "service_factor_f4.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(int(r["temp_c"]), int(r["ed_pct"]))] = float(r["f4"])
    return out


@lru_cache(maxsize=1)
def _f5_table() -> dict[tuple[int, int], float]:
    out = {}
    with open(DATA_DIR / "service_factor_f5.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(int(r["temp_c"]), int(r["ed_pct"]))] = float(r["f5"])
    return out


@lru_cache(maxsize=1)
def _f8_table() -> dict[str, float]:
    out = {}
    with open(DATA_DIR / "service_factor_f8.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["lubrication"]] = float(r["f8"])
    return out


# ---------- 查询 API ----------


def lookup_f1(application_key: str, hours_per_day: float, custom: float | None = None) -> float:
    if application_key == "custom":
        if custom is None:
            raise ValueError("application_key='custom' 时必须提供 custom_f1")
        return float(custom)
    row = _f1_table().get(application_key)
    if not row:
        raise KeyError(f"未知 application_key: {application_key}")
    band = _hour_band(hours_per_day)
    field = {"le_0_5": "f1_le_0_5h", "le_10": "f1_le_10h", "gt_10": "f1_gt_10h"}[band]
    v = row.get(field, "")
    if not v:
        raise ValueError(
            f"应用 {row['name_cn']} 在 {band} 时段无 f1 数据,请改选时段或提供自定义系数"
        )
    return float(v)


def lookup_f2(prime_mover: str) -> float:
    return _f2_table()[prime_mover]


def lookup_f3(starts_per_hour: int, load_direction: str) -> float:
    band = _starts_band(starts_per_hour)
    return _f3_table()[band][load_direction]


def lookup_f4(temp_c: int, ed_pct: int) -> float:
    """带自然/风冷的温度系数。"""
    return _f4_table()[(temp_c, ed_pct)]


def lookup_f5(temp_c: int, ed_pct: int) -> float:
    """带水冷盘管的温度系数。"""
    return _f5_table()[(temp_c, ed_pct)]


def lookup_f8(lubrication: str) -> float:
    return _f8_table()[lubrication]


def list_applications() -> list[tuple[str, str]]:
    """返回所有可选应用的 (key, name_cn) 列表,供 UI 下拉用。"""
    rows = list(_f1_table().values())
    return [(r["application_key"], r["name_cn"]) for r in rows]
