# Rock 齿轮箱自动选型程序

基于 **ROCK / DODGE®** 工业齿轮箱样本手册(`docs/Rock.pdf`)的 Web 选型工具。
输入工况、负载、安装与环境条件,自动推荐**最佳齿轮箱型号**并生成完整的 Word 选型计算书与外形/安装尺寸图。

---

## 功能特性

- ✅ **完全复现手册第 8-9 页选型流程**(传动比 → 服务系数 → 扭矩/功率/寿命/热功率校核)
- ✅ 内置 Rock.pdf 全部 5 个系列、40 种公称速比、3-18 机座号的目录数据
- ✅ 自动选最小够用机座号(扭矩 + 4 种散热方案逐级尝试)
- ✅ 生成中文 Word 选型计算书(含完整公式代入、校核结论、外形图)
- ✅ matplotlib 绘制外形/安装尺寸示意图(主视图 + 俯视图)
- ✅ Streamlit Web UI,浏览器一键使用

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行单元测试(应全部通过)
pytest tests/ -v

# 3. 启动 Web 应用
streamlit run app.py
# → 浏览器打开 http://localhost:8501
```

### 验证算法:手册标准算例

打开浏览器后,**默认参数已预填手册第 9 页的"选型案例"**:

| 输入 | 值 |
|---|---|
| P₁ | 150 kW |
| P₂ | 140 kW |
| n₁ | 1500 r/min |
| n₂ | 26 r/min |
| T_A | 1440 N·m |
| 工作机 | 皮带输送机 ≤150 kW |
| ED / 每日小时 / 启停 | 100% / 12 h / 7 次 |
| 系列 / 输出轴 / 安装 | RKB / S / H |
| 环境温度 | 30°C |

点 **"开始选型计算"** 应得出:

> **RKB3SH 12-56**,需要冷却风扇(GF),扭矩利用率 ≈ 38%

与手册第 9 页结论完全一致。

---

## 目录结构

```
Rock/
├── app.py                    # Streamlit 主入口
├── requirements.txt
├── README.md                 # 本文件
├── docs/
│   └── Rock.pdf              # 55 页 ROCK 样本手册
├── rock_gearbox/             # Python 核心包
│   ├── models.py             # SelectionInput / SelectionResult / Gearbox dataclass
│   ├── catalog.py            # CSV 加载与候选筛选
│   ├── service_factor.py     # f1~f8 查表
│   ├── selector.py           # 选型算法(对照手册 p.8-9)
│   ├── drawing.py            # matplotlib 外形图
│   └── report.py             # python-docx 选型计算书
├── data/                     # 目录数据 CSV(详见 data/README.md)
│   ├── series.csv
│   ├── ratio_torque.csv      # 主表 817 行
│   ├── thermal_power.csv     # 热功率(本期 33 行,需补全)
│   ├── dimensions.csv        # 外形尺寸(本期 7 行,需补全)
│   ├── service_factor_f1.csv # 30 个典型应用
│   ├── service_factor_f2~8.csv
│   └── README.md             # 数据表说明与待补充清单
├── scripts/
│   └── extract_catalog.py    # 从 Rock.pdf 重新生成 CSV(数据更新时用)
└── tests/
    └── test_selector.py      # 包含手册标准算例的核心测试
```

---

## 数据补全指引

本期版本的数据覆盖以**跑通手册标准算例**为最低要求。**完整产品数据需逐步补全**:

| 数据 | 现状 | 补全方法 |
|---|---|---|
| 公称速比 / 实际速比 / T₂N | **完整**(覆盖所有公称速比 × 机座号) | 已可用 |
| 热功率 P_GN/F/C/FC | 仅 RKB 系列 i_N ∈ {31.5, 40, 56} | 编辑 `scripts/extract_catalog.py` 中 `RKB_PG` dict,补 RKH 与其他速比的数据后重跑 |
| 外形尺寸 | 仅 7 个代表型号 | 对照 `docs/Rock.pdf` 第 24-47 页,补 `dimensions.csv` |
| f1 应用 | 30 个典型应用 | 对照 PDF 第 10 页表 1,继续添加 |

补完数据后:

```bash
python scripts/extract_catalog.py   # 重新生成 CSV
pytest                              # 校验未破坏算例
```

---

## PDF 报告导出(可选)

如需把 Word 计算书转 PDF:

```bash
# Linux 服务端
apt install libreoffice
libreoffice --headless --convert-to pdf 选型计算书.docx

# macOS / Windows 桌面端
# 直接用 Word 打开后 "另存为 PDF"
```

---

## 技术栈

- **Python** 3.11+
- **Streamlit** 1.30+(Web UI)
- **pandas / numpy**(数据加载)
- **python-docx + docxtpl**(Word 报告)
- **matplotlib**(外形图)
- **pytest**(单元测试)

---

## 参考

- `docs/Rock.pdf` — ROCK / DODGE 工业通用齿轮箱样本手册(55 页)
- 算法基准:手册第 8 页选型流程图、第 9 页选型案例
- 标准:ISO 6336(齿轮承载能力计算)
