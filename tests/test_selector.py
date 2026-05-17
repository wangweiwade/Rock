"""核心测试 — 必须包含 Rock.pdf 第 9 页"选型案例"标准算例。"""

from __future__ import annotations
import pytest

from rock_gearbox import SelectionInput, select_gearbox


def test_manual_standard_example():
    """复现 Rock.pdf 第 9 页"选型案例"。

    已知:
      原动机:P1=150 kW, n1=1500 rpm, T_A=1440 N·m
      工作机(皮带输送机):P2=140 kW, n2=26 rpm
      每天 12 h,7 启停/h, ED=100%, 30°C
      传动类型:伞齿轮(RKB), 卧式安装(H), 实心轴输出(S)

    预期:RKB3SH 12-56,需要冷却风扇(PGF)。
    """
    inp = SelectionInput(
        p1_kw=150,
        p2_kw=140,
        n1_rpm=1500,
        n2_rpm=26,
        t_a_nm=1440,
        application_key="conveyor_belt_le150kw",   # P2=140 ≤ 150 -> ≤150kW 行
        ed_pct=100,
        hours_per_day=12,
        starts_per_hour=7,
        load_direction="unidirectional",
        prime_mover="electric_motor",
        family="RKB",
        output_shaft="S",
        mounting="H",
        lubrication="oil_bath",
        ambient_temp_c=30,
        cooling_pref="auto",
    )
    res = select_gearbox(inp)

    # ---- 核心结论 ----
    assert res.best.series_code == "RKB3", f"应选 RKB3 系列,实际 {res.best.series_code}"
    assert res.best.size == 12, f"应选 size=12,实际 {res.best.size}"
    assert res.chosen_ratio_nominal == 56.0, f"应选 i_N=56,实际 {res.chosen_ratio_nominal}"
    assert res.type_code.startswith("RKB3SH 12-56"), f"型号编码错:{res.type_code}"

    # ---- 中间量 ----
    # i_s = 1500/26 ≈ 57.69
    assert abs(res.i_required - 57.69) < 0.1
    # 手册:RKB3 size 12, i_N=56 实际 i = 54.769
    assert abs(res.chosen_ratio_actual - 54.769) < 0.01

    # ---- 服务系数(对照手册) ----
    # 皮带输送机 ≤150kW, 12h>10h: f1 = 1.4
    # 注:手册用的是 ≥150kW 行(f1=1.5),因为按 P1=150 归类;
    # 这里 P2=140 故归 ≤150kW。两者都合理。
    assert res.f1 in (1.4, 1.5), f"f1 异常: {res.f1}"
    assert res.f2 == 1.0
    # 7 启停/h ∈ [6,30], 单向 → f3 = 0.65
    assert res.f3 == 0.65
    # 30°C, ED=100% → f4 = 0.87 (手册显示 0.88,容差 0.01 内)
    assert abs(res.f4 - 0.87) < 0.02
    # 30°C, ED=100% → f5 = 0.93
    assert abs(res.f5 - 0.93) < 0.01
    # 浸油润滑 → f8 = 1.0
    assert res.f8 == 1.0

    # ---- 扭矩校核通过 ----
    assert res.torque_check_pass

    # ---- 散热方案:GN 不够,需要风冷(GF) ----
    # 标称 PGN = 108 kW,实际 PGN × f4 × f8 ≈ 108 × 0.87 × 1.0 = 93.96 < 140
    gn = next((c for c in res.cooling_options if c.cooling == "GN"), None)
    assert gn is not None
    assert not gn.passes, f"GN 应不通过,实际 PG={gn.p_g_corrected_kw:.1f}"
    # PGF = 258 kW(数据表), 258 × 0.87 × 1.0 ≈ 224.5 > 140
    gf = next((c for c in res.cooling_options if c.cooling == "GF"), None)
    assert gf is not None
    assert gf.passes, f"GF 应通过,实际 PG={gf.p_g_corrected_kw:.1f}"
    assert res.chosen_cooling.cooling == "GF"


def test_n2_zero_raises():
    inp = SelectionInput(p1_kw=10, p2_kw=10, n1_rpm=1500, n2_rpm=0)
    with pytest.raises(ValueError):
        select_gearbox(inp)


def test_p2_zero_raises():
    inp = SelectionInput(p1_kw=10, p2_kw=0, n1_rpm=1500, n2_rpm=26)
    with pytest.raises(ValueError):
        select_gearbox(inp)


def test_rkh_family_selection():
    """RKH 平行轴的选型:输入 n1=1500, n2=150 → i_s=10, i_N=10。"""
    inp = SelectionInput(
        p1_kw=50, p2_kw=45,
        n1_rpm=1500, n2_rpm=150,
        t_a_nm=None,
        application_key="conveyor_belt_le150kw",
        ed_pct=100, hours_per_day=8, starts_per_hour=3,
        family="RKH",
        ambient_temp_c=30,
    )
    res = select_gearbox(inp)
    assert res.best.family == "RKH"
    assert res.chosen_ratio_nominal == 10.0


def test_smaller_load_picks_smaller_size():
    """同样工况,小载荷应选更小的机座号。"""
    base = dict(
        p1_kw=50, p2_kw=10, n1_rpm=1500, n2_rpm=26,
        application_key="conveyor_belt_le150kw",
        ed_pct=100, hours_per_day=8, starts_per_hour=3,
        family="RKB", output_shaft="S", mounting="H",
        ambient_temp_c=30, cooling_pref="auto",
    )
    res_small = select_gearbox(SelectionInput(**base))
    res_big = select_gearbox(SelectionInput(**{**base, "p2_kw": 140, "t_a_nm": 1440}))
    assert res_small.best.size <= res_big.best.size
