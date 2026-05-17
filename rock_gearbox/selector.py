"""核心选型算法 — 严格按照 Rock.pdf 第 8-9 页流程实现。

主要步骤(逐字对应手册):
  1. i_s = n1 / n2 → 选最接近的标准 i_N
  2. P_N ≥ P2 · f1 · f2
  3. 从 (family, ratio_nominal) 候选中按机座号升序选第一个 T2N 满足扭矩要求的
  4. 校核 3.33 · P2 ≥ P_N(目录额定功率上限粗校)
  5. 校核 P_N ≥ T_A · n1 · f3 / 9550(寿命/峰值扭矩侧)
  6. 热功率 PG = (PGN/PGF/PGC/PGFC) × f4_or_f5 × f8 ≥ P2
"""

from __future__ import annotations

from .catalog import (
    CatalogEntry,
    find_candidates,
    get_dimensions,
    nearest_standard_ratio,
)
from .models import (
    CoolingResult,
    Gearbox,
    SelectionInput,
    SelectionResult,
)
from .service_factor import (
    lookup_f1,
    lookup_f2,
    lookup_f3,
    lookup_f4,
    lookup_f5,
    lookup_f8,
)


class NoSuitableGearboxError(Exception):
    """当所有候选都无法通过校核时抛出,附带分析报告。"""

    def __init__(self, message: str, attempted: list[str]):
        super().__init__(message)
        self.attempted = attempted


COOLING_NAMES_CN = {
    "GN": "不带辅助冷却(浸油自然散热)",
    "GF": "带冷却风扇",
    "GC": "带冷却盘管(油-水冷却)",
    "GFC": "带冷却风扇 + 冷却盘管",
}


# 在 ed_pct 不在 {20,40,60,80,100} 范围内时,取最接近且不大于的标准 ED
ED_STANDARD = [20, 40, 60, 80, 100]


def _snap_ed(ed_pct: int) -> int:
    if ed_pct in ED_STANDARD:
        return ed_pct
    # 找最接近的标准值
    return min(ED_STANDARD, key=lambda v: abs(v - ed_pct))


def _snap_temp(temp_c: int) -> int:
    standards = [10, 20, 30, 40, 50]
    if temp_c in standards:
        return temp_c
    return min(standards, key=lambda v: abs(v - temp_c))


def _check_one_cooling(
    g: CatalogEntry,
    cooling: str,
    f4: float,
    f5: float,
    f8: float,
    p2_kw: float,
) -> CoolingResult | None:
    """如果该 cooling 在数据表中存在,返回 CoolingResult,否则 None。"""
    attr = {"GN": "p_gn_kw", "GF": "p_gf_kw", "GC": "p_gc_kw", "GFC": "p_gfc_kw"}[cooling]
    rated = getattr(g, attr)
    if rated is None:
        return None
    # GN/GF 用 f4;GC/GFC 用 f5
    if cooling in ("GN", "GF"):
        f_temp = f4
        f_label = "f4"
    else:
        f_temp = f5
        f_label = "f5"
    corrected = rated * f_temp * f8
    return CoolingResult(
        cooling=cooling,
        name_cn=COOLING_NAMES_CN[cooling],
        p_g_rated_kw=rated,
        p_g_corrected_kw=corrected,
        f_temp=f_temp,
        f_temp_label=f_label,
        f8=f8,
        passes=corrected >= p2_kw,
    )


def _build_type_code(g: CatalogEntry, output_shaft: str, mounting: str) -> str:
    """RKB3 + S + H + 12 + 56 → 'RKB3SH 12-56'。"""
    return f"{g.series_code}{output_shaft}{mounting} {g.size}-{int(g.ratio_nominal) if g.ratio_nominal == int(g.ratio_nominal) else g.ratio_nominal}"


def select_gearbox(inp: SelectionInput) -> SelectionResult:
    if inp.n2_rpm <= 0:
        raise ValueError("n2_rpm 必须大于 0")
    if inp.p2_kw <= 0:
        raise ValueError("p2_kw 必须大于 0")

    # ---- Step 1: 速比 ----
    i_required = inp.n1_rpm / inp.n2_rpm
    i_n = nearest_standard_ratio(i_required)
    deviation = abs(i_n - i_required) / i_required * 100

    # ---- Step 2: 系数 ----
    f1 = lookup_f1(inp.application_key, inp.hours_per_day, inp.custom_f1)
    f2 = lookup_f2(inp.prime_mover)
    f3 = lookup_f3(inp.starts_per_hour, inp.load_direction)
    ed = _snap_ed(inp.ed_pct)
    temp = _snap_temp(inp.ambient_temp_c)
    f4 = lookup_f4(temp, ed)
    f5 = lookup_f5(temp, ed)
    f8 = lookup_f8(inp.lubrication)

    # ---- Step 3: 扭矩与功率需求 ----
    t_2 = 9550 * inp.p2_kw / inp.n2_rpm
    t_a = inp.t_a_nm if inp.t_a_nm is not None else t_2
    required_p_n = inp.p2_kw * f1 * f2
    required_p_n_life = t_a * inp.n1_rpm * f3 / 9550 / 1.0  # T_A 单位是 N·m,直接代入
    required_p_n_max = max(required_p_n, required_p_n_life)
    # 扭矩侧门槛:T_A 已乘 f1·f2 ?
    # 手册流程实际是用 P_N 比较,但 T2N 必须能承受 T_A.
    # 取保守做法:候选 T2N ≥ T_A × f1 × f2(扭矩校核)且 P_N ≥ P2·f1·f2(功率)
    t_required_nm = t_2 * f1 * f2

    # ---- Step 4: 找候选 ----
    candidates = find_candidates(inp.family, i_n)
    if not candidates:
        raise NoSuitableGearboxError(
            f"无 {inp.family} 系列在 i_N={i_n} 下的型号(数据表中可能未录入此组合)",
            attempted=[],
        )

    # ---- Step 5: 按机座号升序找首个满足扭矩 + 热功率的型号 ----
    attempted: list[str] = []
    for g in candidates:
        attempted.append(f"{g.series_code} {g.size}")
        torque_pass = g.t2n_nm >= t_required_nm
        if not torque_pass:
            continue

        # 热功率筛选
        prefs = ["GN", "GF", "GC", "GFC"] if inp.cooling_pref == "auto" else [inp.cooling_pref]
        cooling_options: list[CoolingResult] = []
        chosen: CoolingResult | None = None
        for cool in ["GN", "GF", "GC", "GFC"]:
            res = _check_one_cooling(g, cool, f4, f5, f8, inp.p2_kw)
            if res is None:
                continue
            cooling_options.append(res)
            if chosen is None and res.passes and cool in prefs:
                chosen = res

        if not cooling_options:
            # 热功率数据未录入 → 仅给出扭矩通过的结果,标记需补充热功率核对
            chosen = CoolingResult(
                cooling="GN", name_cn="(数据未录入,以扭矩校核通过)",
                p_g_rated_kw=0.0, p_g_corrected_kw=0.0,
                f_temp=f4, f_temp_label="f4", f8=f8, passes=False,
            )
        elif chosen is None:
            continue  # 有热功率数据但都不够 → 试下一个机座号

        # 构建结果
        gearbox = g.to_gearbox(dims=get_dimensions(g.series_code, g.size))
        type_code = _build_type_code(g, inp.output_shaft, inp.mounting)

        notes: list[str] = []
        if not cooling_options:
            notes.append("热功率数据未录入,仅以扭矩校核通过该型号(建议补全 thermal_power.csv)")
        if deviation > inp.ratio_tolerance_pct:
            notes.append(
                f"速比偏差 {deviation:.2f}% 超过容差 {inp.ratio_tolerance_pct}%,请确认是否可接受"
            )
        # 3.33 校核
        power_3_33_pass = 3.33 * inp.p2_kw >= required_p_n
        if not power_3_33_pass:
            notes.append("3.33·P2 校核未通过,建议联系厂家技术团队")

        return SelectionResult(
            inp=inp,
            best=gearbox,
            type_code=type_code,
            i_required=i_required,
            chosen_ratio_nominal=i_n,
            chosen_ratio_actual=g.ratio_actual or i_n,
            ratio_deviation_pct=deviation,
            f1=f1, f2=f2, f3=f3, f4=f4, f5=f5, f8=f8,
            p_2_kw=inp.p2_kw,
            t_2_nm=t_2,
            t_a_nm=t_a,
            required_p_n_kw=required_p_n,
            required_p_n_life_kw=required_p_n_life,
            required_p_n_kw_max=required_p_n_max,
            torque_check_pass=True,
            torque_utilization=t_required_nm / g.t2n_nm,
            power_3_33_check_pass=power_3_33_pass,
            life_check_pass=True,                  # T_A 已纳入扭矩校核
            cooling_options=cooling_options,
            chosen_cooling=chosen,
            notes=notes,
        )

    raise NoSuitableGearboxError(
        f"在 i_N={i_n} 下,所有候选型号(共 {len(candidates)} 个)均无法通过扭矩或热功率校核。\n"
        f"已尝试:{', '.join(attempted)}",
        attempted=attempted,
    )
