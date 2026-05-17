"""Rock 齿轮箱自动选型程序 — Streamlit Web 主入口。

运行方式:
    streamlit run app.py
"""

from __future__ import annotations
import streamlit as st

from rock_gearbox import (
    SelectionInput,
    NoSuitableGearboxError,
    select_gearbox,
)
from rock_gearbox.models import LAYOUT_OPTIONS
from rock_gearbox.service_factor import list_applications
from rock_gearbox.drawing import render_drawing, render_dimensions_table, get_drawing_page
from rock_gearbox.report import generate_report


st.set_page_config(
    page_title="Rock 齿轮箱自动选型",
    page_icon="⚙️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# 侧边栏:项目信息
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Rock 齿轮箱选型")
    st.caption("基于 ROCK / DODGE® 工业齿轮箱样本手册")
    st.divider()
    st.subheader("项目信息")
    project_name = st.text_input("项目名称", value="")
    customer = st.text_input("客户单位", value="")
    engineer = st.text_input("工程师", value="")
    st.divider()
    st.caption("数据基于 docs/Rock.pdf 提取(55 页)")


st.title("Rock 齿轮箱自动选型程序")
st.caption("根据工况、负载、安装与环境条件,自动推荐最佳齿轮箱型号并生成完整选型计算书")


# ---------------------------------------------------------------------------
# 输入参数 (4 个分组)
# ---------------------------------------------------------------------------

# 默认值采用手册第 9 页"选型案例"工况(便于一键演示)
APPS = list_applications()
APP_LABELS = {k: f"{name} [{k}]" for k, name in APPS}

with st.expander("① 工况 / Working condition", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    p1_kw = c1.number_input("电机功率 P₁ (kW)", min_value=0.1, value=150.0, step=10.0)
    p2_kw = c2.number_input("工作机功率 P₂ (kW)", min_value=0.1, value=140.0, step=10.0)
    n1_rpm = c3.number_input("输入转速 n₁ (r/min)", min_value=1.0, value=1500.0, step=100.0)
    n2_rpm = c4.number_input("输出转速 n₂ (r/min)", min_value=0.1, value=26.0, step=1.0)
    t_a_input = st.number_input(
        "最大启动/峰值扭矩 T_A (N·m,留空则按 P₂/n₂ 计算)",
        min_value=0.0, value=1440.0, step=100.0,
    )

with st.expander("② 负载与服务系数", expanded=True):
    c1, c2 = st.columns(2)
    app_key = c1.selectbox(
        "工作机类型(决定 f₁)",
        options=[k for k, _ in APPS],
        format_func=lambda k: APP_LABELS[k],
        index=[k for k, _ in APPS].index("conveyor_belt_le150kw"),
    )
    custom_f1 = None
    if app_key == "custom":
        custom_f1 = c1.number_input("自定义 f₁", min_value=0.5, max_value=3.0, value=1.5, step=0.05)
    prime_mover = c2.selectbox(
        "原动机类型(f₂)",
        options=["electric_motor", "multi_cylinder", "single_cylinder"],
        format_func=lambda x: {"electric_motor": "电机/液压马达/汽轮机 (1.0)",
                                "multi_cylinder": "多缸发动机 (1.25)",
                                "single_cylinder": "单缸发动机 (1.5)"}[x],
    )
    c1, c2, c3, c4 = st.columns(4)
    ed_pct = c1.selectbox("每小时工作周期 ED (%)", [20, 40, 60, 80, 100], index=4)
    hours_per_day = c2.number_input("每日运行小时数", min_value=0.5, max_value=24.0, value=12.0, step=1.0)
    starts_per_hour = c3.number_input("每小时启停次数", min_value=0, value=7, step=1)
    load_direction = c4.selectbox(
        "负载方向(f₃)", ["unidirectional", "alternating"],
        format_func=lambda x: {"unidirectional": "单向载荷", "alternating": "交变载荷"}[x],
    )

with st.expander("③ 结构 / Structure", expanded=True):
    c1, c2, c3 = st.columns(3)
    family = c1.selectbox(
        "系列家族", ["RKB", "RKH", "auto"],
        format_func=lambda x: {"RKB": "RKB 直交轴(伞齿轮)",
                                "RKH": "RKH 平行轴(斜齿)",
                                "auto": "不限"}[x],
        index=0,
    )
    output_shaft = c2.selectbox(
        "输出轴形式", ["S", "H", "D"],
        format_func=lambda x: {"S": "S 实心轴", "H": "H 空心轴", "D": "D 空心+收缩盘"}[x],
    )
    mounting = c3.selectbox(
        "安装方位", ["H", "M"],
        format_func=lambda x: {"H": "H 卧式带地脚", "M": "M 卧式无地脚"}[x],
        help="⚠️ M 形式(卧式无地脚)仅在 size 13-18 大型号上提供;"
             "若选型结果指向小尺寸但您选了 M,程序会提示无可用型号。",
    )
    if mounting == "M":
        st.info("ℹ️ 您选了 **M 形式(卧式无地脚)**,该形式仅 size 13-18 大型号提供。"
                "若工况扭矩较小可能找不到匹配型号,届时请改选 H 形式。")

    # 布局形式依赖于输出轴(对照 Rock.pdf 第 51 页)
    layout_options = LAYOUT_OPTIONS[output_shaft]
    layout_default_idx = layout_options.index("C") if "C" in layout_options else 0
    c1, c2 = st.columns(2)
    layout = c1.selectbox(
        f"布局形式(输出轴朝向,见手册第 51 页)— {output_shaft} 类有 {len(layout_options)} 种",
        layout_options,
        index=layout_default_idx,
        help="🔍 实心轴 S 可选 A/B/C/D 四种;空心轴 H 与带锁紧盘空心轴 D 各仅 A/B 两种。"
             "完整图示见 Rock.pdf 第 51 页《布局形式》。"
             "字母代表输出轴端面朝向:A/B 通常指左右,C/D 指上下。",
    )
    lubrication = c2.selectbox(
        "润滑方式(f₈)", ["oil_bath", "forced"],
        format_func=lambda x: {"oil_bath": "浸油 (1.0)", "forced": "强制 (1.05)"}[x],
    )

with st.expander("④ 环境 / Environment", expanded=True):
    c1, c2 = st.columns(2)
    ambient_temp_c = c1.selectbox("环境温度 (°C)", [10, 20, 30, 40, 50], index=2)
    cooling_pref = c2.selectbox(
        "散热方式偏好",
        ["auto", "GN", "GF", "GC", "GFC"],
        format_func=lambda x: {
            "auto": "自动(从低到高选)",
            "GN": "GN 无辅助冷却",
            "GF": "GF 风冷",
            "GC": "GC 水冷盘管",
            "GFC": "GFC 风冷+水冷",
        }[x],
    )


# ---------------------------------------------------------------------------
# 计算按钮
# ---------------------------------------------------------------------------

st.divider()
run = st.button("🚀  开始选型计算", type="primary", use_container_width=True)

if run:
    try:
        inp = SelectionInput(
            p1_kw=p1_kw, p2_kw=p2_kw,
            n1_rpm=n1_rpm, n2_rpm=n2_rpm,
            t_a_nm=t_a_input if t_a_input > 0 else None,
            application_key=app_key, custom_f1=custom_f1,
            ed_pct=int(ed_pct),
            hours_per_day=hours_per_day, starts_per_hour=int(starts_per_hour),
            load_direction=load_direction,
            prime_mover=prime_mover,
            family=family, output_shaft=output_shaft, mounting=mounting, layout=layout,
            lubrication=lubrication,
            ambient_temp_c=int(ambient_temp_c), cooling_pref=cooling_pref,
        )
        res = select_gearbox(inp)
        st.session_state["result"] = res
        st.session_state["inputs"] = {
            "project_name": project_name, "customer": customer, "engineer": engineer,
        }
    except NoSuitableGearboxError as e:
        st.error(f"❌ 选型失败:{e}\n\n已尝试候选:{', '.join(e.attempted) if e.attempted else '(无)'}")
        st.session_state.pop("result", None)
    except Exception as e:
        st.exception(e)
        st.session_state.pop("result", None)


# ---------------------------------------------------------------------------
# 结果展示
# ---------------------------------------------------------------------------

if "result" in st.session_state:
    res = st.session_state["result"]
    meta = st.session_state.get("inputs", {})

    # 顶部大卡片
    st.success(f"✅  推荐型号:**{res.type_code}**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("额定输出扭矩 T₂N", f"{res.best.t2n_nm/1000:.1f} kN·m")
    c2.metric("实际传动比 i", f"{res.best.ratio_actual:.3f}")
    c3.metric("扭矩利用率", f"{res.torque_utilization*100:.1f} %")
    c4.metric("散热方式", res.chosen_cooling.cooling)

    if res.notes:
        with st.container():
            for n in res.notes:
                st.warning(f"⚠️ {n}")

    tab_calc, tab_dim, tab_dl = st.tabs(["📐 计算过程", "📏 外形/安装图", "📥 下载计算书"])

    # ---- Tab 1:计算过程 ----
    with tab_calc:
        st.markdown(f"### 4.1 传动比")
        st.latex(r"i_s = \frac{n_1}{n_2} = \frac{%g}{%g} = %.3f" %
                 (res.inp.n1_rpm, res.inp.n2_rpm, res.i_required))
        st.write(f"取最接近的标准 $i_N$ = **{res.chosen_ratio_nominal}**(偏差 {res.ratio_deviation_pct:.2f}%)")
        st.write(f"实际传动比 i = **{res.chosen_ratio_actual:.3f}**")

        st.markdown(f"### 4.2 服务系数")
        st.table({
            "系数": ["f₁ 工况", "f₂ 原动机", "f₃ 峰值扭矩", "f₄ 自然/风冷", "f₅ 水冷", "f₈ 供油"],
            "取值": [res.f1, res.f2, res.f3, res.f4, res.f5, res.f8],
        })

        st.markdown(f"### 4.3 输出扭矩")
        st.latex(r"T_2 = \frac{9550 \cdot P_2}{n_2} = \frac{9550 \times %g}{%g} = %.1f\ \text{N·m}" %
                 (res.inp.p2_kw, res.inp.n2_rpm, res.t_2_nm))

        st.markdown(f"### 4.4 所需额定功率(扭矩侧)")
        st.latex(r"P_N \geq P_2 \cdot f_1 \cdot f_2 = %g \times %g \times %g = %.1f\ \text{kW}" %
                 (res.inp.p2_kw, res.f1, res.f2, res.required_p_n_kw))

        st.markdown(f"### 4.5 寿命/峰值扭矩校核")
        st.latex(r"P_N \geq T_A \cdot n_1 \cdot f_3 / 9550 = %g \times %g \times %g / 9550 = %.1f\ \text{kW}" %
                 (res.t_a_nm, res.inp.n1_rpm, res.f3, res.required_p_n_life_kw))

        st.markdown("### 4.6 热功率校核")
        if res.cooling_options:
            cooling_rows = [
                {
                    "散热": c.cooling,
                    "中文": c.name_cn,
                    "铭牌 P_G (kW)": f"{c.p_g_rated_kw:.1f}",
                    f"× {c.f_temp_label} × f₈": f"{c.f_temp:.2f} × {c.f8:.2f}",
                    "修正 P_G (kW)": f"{c.p_g_corrected_kw:.1f}",
                    "结论": "✅ 通过" if c.passes else "❌ 不足",
                }
                for c in res.cooling_options
            ]
            st.table(cooling_rows)
            st.success(f"**选定散热方式:{res.chosen_cooling.name_cn}**")
        else:
            st.info("热功率数据未录入,本期跳过该校核(请补全 data/thermal_power.csv)")

        st.markdown("### 4.7 推荐型号铭牌")
        st.json({
            "型号编码": res.type_code,
            "系列": res.best.series_code,
            "机座号": res.best.size,
            "公称速比 i_N": res.best.ratio_nominal,
            "实际速比 i": round(res.best.ratio_actual, 3),
            "额定输出扭矩 T₂N (N·m)": res.best.t2n_nm,
            "热功率 P_GN (kW)": res.best.p_gn_kw,
            "热功率 P_GF (kW)": res.best.p_gf_kw,
            "热功率 P_GC (kW)": res.best.p_gc_kw,
            "热功率 P_GFC (kW)": res.best.p_gfc_kw,
        })

    # ---- Tab 2:外形图(直接截取 Rock.pdf 中的官方页) ----
    with tab_dim:
        page_no = get_drawing_page(res.best.series_code, res.best.size)
        if page_no:
            st.caption(f"📖 来源:**Rock.pdf 第 {page_no} 页**(外形图)与第 {page_no + 1} 页(尺寸表)")
        png_bytes = render_drawing(res.best, res.type_code)
        st.image(png_bytes, caption=f"{res.type_code} 外形图")

        dim_png = render_dimensions_table(res.best)
        if dim_png:
            with st.expander(f"📐 查看尺寸数据表(Rock.pdf 第 {page_no + 1} 页)", expanded=False):
                st.image(dim_png, caption=f"{res.best.series_code} {res.best.size} 详细尺寸表")

    # ---- Tab 3:下载 ----
    with tab_dl:
        png_bytes = render_drawing(res.best, res.type_code)
        docx_bytes = generate_report(
            res,
            project_name=meta.get("project_name", ""),
            customer=meta.get("customer", ""),
            engineer=meta.get("engineer", ""),
            image_png_bytes=png_bytes,
        )
        st.download_button(
            label="📄  下载 Word 选型计算书",
            data=docx_bytes,
            file_name=f"Rock选型计算书_{res.type_code.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.caption("如需 PDF,Linux 服务端可安装 LibreOffice:`apt install libreoffice`,"
                   "然后用 `libreoffice --headless --convert-to pdf` 转换。")
        st.download_button(
            label="🖼️  下载外形图 (PNG)",
            data=png_bytes,
            file_name=f"Rock外形图_{res.type_code.replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True,
        )
