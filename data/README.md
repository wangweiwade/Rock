# Rock 齿轮箱选型程序 — 数据表说明

本目录的 CSV 文件由 `scripts/extract_catalog.py` 从 `docs/Rock.pdf` 抽取生成。
**所有运行时数据均来自这些 CSV;PDF 仅作参考存档。** 替换数据时直接编辑 CSV 即可。

## 文件清单

| 文件 | 内容 | PDF 参考页 |
|---|---|---|
| `series.csv` | 5 个系列定义(RKH1/2/3, RKB2/3)及机座号范围 | p.5 型号编码 |
| `ratio_torque.csv` | 主表:`(系列, 机座号, 公称速比)` → `(实际速比, 额定输出扭矩 T2N)` | p.22-23 (T2N)、p.49-50 (i) |
| `thermal_power.csv` | 热功率表:`(系列, 机座号, 公称速比)` → `(PGN, PGF, PGC, PGFC)` | p.13/15/17/19/21 |
| `dimensions.csv` | 关键外形/安装尺寸,用于绘图与重量估算 | p.24-47 |
| `service_factor_f1.csv` | 服务系数 f1:应用类型 × 每日运转时长 | p.10 表 1 |
| `service_factor_f2.csv` | 原动机系数 f2 | p.11 表 2 |
| `service_factor_f3.csv` | 峰值扭矩系数 f3 | p.11 表 3 |
| `service_factor_f4.csv` | 环境温度系数 f4(自然/风冷) | p.11 表 4 |
| `service_factor_f5.csv` | 环境温度系数 f5(水冷) | p.11 表 5 |
| `service_factor_f8.csv` | 供油系数 f8 | p.11 表 6 |

## 已录入的覆盖范围

**本期版本以"跑通手册标准算例(RKB3SH 12-56)"为最低要求,数据覆盖如下:**

### `ratio_torque.csv` — 几乎全覆盖
- RKH 系列:所有公称速比 1.25 ~ 112,所有机座号 3 ~ 18
- RKB 系列:所有公称速比 5 ~ 90,所有机座号 4 ~ 18
- 缺失格(在 PDF 中标 `-` 或留空的型号)未录入

### `thermal_power.csv` — 当前覆盖情况
- **RKB 系列**:96.9% 覆盖(346/357 个组合,涵盖 i_N 5 ~ 90 几乎全部)
- **RKH 系列**:17.6% 覆盖(81/460 个组合,主要是 i_N 1.25 ~ 5.6)

完整覆盖清单与缺失明细见 **`data/COVERAGE.md`**(由 `scripts/extract_catalog.py` 自动生成)。

**补全方法**:编辑 `scripts/parse_thermal_power.py` 顶部的 `MANUAL_PG` 字典,
新增形如 `("RKB", 56.0, 12): (108, 258, 342, 484)` 的条目(对应 PGN/PGF/PGC/PGFC)。
数据源:Rock.pdf 第 13/15/17/19/21 页。运行 `python scripts/parse_thermal_power.py` 重新生成 CSV。

**程序行为**:若选型时某型号在 `thermal_power.csv` 中没有记录,
程序仍会基于扭矩通过该型号,但会显示"热功率数据未录入"的提示。

### `dimensions.csv` — 仅 7 行代表性数据
用于演示外形图功能。完整尺寸需对照 PDF 第 24-47 页录入。

### `service_factor_f1.csv` — 已录入 30 个典型应用
包含皮带输送机、风机、提升机构、搅拌机等工程上最常见的工况。
完整应用清单见 PDF 第 10 页表 1,如需更多可继续添加。

## 重新生成

```bash
python scripts/extract_catalog.py
```
脚本中所有数据都以 Python dict 字面值的形式硬编码(手工从 PDF 录入),
不依赖运行时再次解析 PDF。这样数据更可信、易审计、易增量补全。
