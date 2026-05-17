"""选型程序的核心数据结构。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


LoadType = Literal["unidirectional", "alternating"]
Family = Literal["RKH", "RKB", "auto"]
OutputShaft = Literal["S", "H", "D"]
Mounting = Literal["H", "M"]
Lubrication = Literal["oil_bath", "forced"]
Cooling = Literal["GN", "GF", "GC", "GFC"]
CoolingPref = Literal["auto", "GN", "GF", "GC", "GFC"]


@dataclass
class SelectionInput:
    # ---- 工况 ----
    p1_kw: float                       # 电机功率 (kW)
    p2_kw: float                       # 工作机轴功率 (kW)
    n1_rpm: float                      # 输入转速 (r/min)
    n2_rpm: float                      # 输出转速 (r/min)
    t_a_nm: float | None = None        # 最大启动/峰值扭矩 (N·m),None 表示用 P2/n2 计算
    # ---- 负载 ----
    application_key: str = "conveyor_belt_le150kw"   # f1 应用键
    custom_f1: float | None = None     # 当 application_key=="custom" 时使用
    ed_pct: int = 100                  # 每小时工作周期 % {20, 40, 60, 80, 100}
    hours_per_day: float = 12          # 每日有效运行小时数
    starts_per_hour: int = 7           # 每小时启停次数
    load_direction: LoadType = "unidirectional"
    # ---- 原动机 ----
    prime_mover: Literal["electric_motor", "multi_cylinder", "single_cylinder"] = "electric_motor"
    # ---- 结构 ----
    family: Family = "RKB"             # 系列家族:RKH 平行轴 / RKB 直交轴 / auto 不限
    output_shaft: OutputShaft = "S"    # 输出轴:S 实心,H 空心,D 空心+收缩盘
    mounting: Mounting = "H"           # 安装方位:H 卧式,M 立式
    lubrication: Lubrication = "oil_bath"
    # ---- 环境 ----
    ambient_temp_c: int = 30           # {10, 20, 30, 40, 50}
    cooling_pref: CoolingPref = "auto"
    # ---- 速比容差 ----
    ratio_tolerance_pct: float = 5.0   # 实际 i_actual 与要求 i_s 的容差(%)


@dataclass
class Gearbox:
    family: str
    stage: int
    series_code: str                   # RKH1 / RKH2 / RKH3 / RKB2 / RKB3
    size: int                          # 4 ~ 18
    ratio_nominal: float               # i_N
    ratio_actual: float                # i 实际
    t2n_nm: float                      # 额定输出扭矩 N·m
    p_gn_kw: float | None = None
    p_gf_kw: float | None = None
    p_gc_kw: float | None = None
    p_gfc_kw: float | None = None
    weight_kg: float | None = None
    dims: dict[str, float] = field(default_factory=dict)


@dataclass
class CoolingResult:
    cooling: Cooling                   # GN / GF / GC / GFC
    name_cn: str
    p_g_rated_kw: float                # 铭牌热功率
    p_g_corrected_kw: float            # 修正后热功率(× f4/f5 × f8)
    f_temp: float                      # f4 或 f5
    f_temp_label: str                  # "f4" / "f5"
    f8: float
    passes: bool                       # PG ≥ P2


@dataclass
class SelectionResult:
    inp: SelectionInput
    best: Gearbox
    type_code: str                     # 例:RKB3SH 12-56
    # ---- 计算中间量 ----
    i_required: float                  # n1 / n2
    chosen_ratio_nominal: float        # 标准 i_N
    chosen_ratio_actual: float         # 实际 i
    ratio_deviation_pct: float
    f1: float
    f2: float
    f3: float
    f4: float                          # 30°C/100% 等查得
    f5: float
    f8: float
    p_2_kw: float
    t_2_nm: float                      # 9550 * P2 / n2
    t_a_nm: float                      # 校核用峰值扭矩
    required_p_n_kw: float             # P2·f1·f2
    required_p_n_life_kw: float        # TA·n1·f3/9550
    required_p_n_kw_max: float
    # ---- 校核 ----
    torque_check_pass: bool
    torque_utilization: float          # T_required / T2N
    power_3_33_check_pass: bool        # 3.33·P2 ≥ P_N
    life_check_pass: bool              # P_N ≥ TA·n1·f3/9550
    cooling_options: list[CoolingResult]
    chosen_cooling: CoolingResult
    notes: list[str] = field(default_factory=list)
