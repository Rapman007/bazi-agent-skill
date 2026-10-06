# -*- coding: utf-8 -*-
"""
逐月推演扫描器 · 通用版（机械计算层）

用途：对**任意**命局，扫描指定区间内每个"节气月"的月柱、十神、大运、
      与命局四支的关系及喜忌档。**只输出可机械计算的客观事实，不做任何解读。**

与原版 monthly_scan.py 的区别：
  1. 十神表由「日主」自动推导（原版写死壬日主）；
  2. 三会 / 三合 / 半合 / 冲 / 刑 / 害 全部按命局四支**通用计算**（原版写死某命局的 GROUP）；
  3. 大运、喜忌干支集合改为命令行传入。

用法（⚠️ 下方**全部为示例假盘的假值**，不源自任何真实命盘）：
    python monthly_scan_gen.py --pillars 甲子,丙寅,戊午,庚申 \
        --dayun "2018-01-01:丁卯,2028-01-01:戊辰,2038-01-01:己巳" \
        --xi 木火 --ji 金水 --xi-zhi 寅卯巳午未戌 --ji-zhi 子亥申酉辰丑 \
        --start 2026-10 --end 2058-12 --out out.md

⚠️ 隔离规约：本脚本**不得写入任何真实命盘的派生量** ——
   包括**起运日 / 大运交界日 / 扫描区间 / 用神忌神逐字集合**。
   这些量不含干支也能反查到人，危险性高于干支本身。

喜忌说明：
  --xi / --ji       天干五行（木火土金水），命中为喜/忌
  --xi-zhi / --ji-zhi  地支集合（十二支逐字写），命中为喜/忌
  不传则默认「喜木火 / 忌金水，燥土未戌偏喜、湿土丑辰偏忌」
"""
import argparse
import os
import sys
from datetime import date, timedelta

# 排盘用同一套口径：**零第三方依赖**（只用标准库 + 本目录 pai_pan.py）。
# 2026-10-06 起不再依赖 lunar_python —— 原来那个包在"立春已过、春节未到"这段
# 会把年柱按农历年写（错），换成 pai_pan 的立春精确时刻口径后一并修掉。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pai_pan as PP

# ---------- 参数 ----------
# ⚠️ 下面 --xi / --ji / --xi-zhi / --ji-zhi / --start / --end 的默认值均为
#    **示例占位**（通用口径，不指向任何具体命盘）。
#    出真实盘时**必须全部显式传入**，不得依赖默认值。
ap = argparse.ArgumentParser()
ap.add_argument("--pillars", required=True, help="四柱，逗号分隔，如 甲子,丙寅,戊午,庚申")
ap.add_argument("--dayun", default="", help="大运，格式 起始日:干支,起始日:干支,…")
ap.add_argument("--xi", default="木火", help="喜神天干五行，如 木火")
ap.add_argument("--ji", default="金水", help="忌神天干五行，如 金水")
ap.add_argument("--xi-zhi", default="寅卯巳午未戌", help="喜神地支集合")
ap.add_argument("--ji-zhi", default="子亥申酉辰丑", help="忌神地支集合")
ap.add_argument("--start", default="2026-10")
ap.add_argument("--end", default="2058-12")
ap.add_argument("--out", default="monthly_out.md")
A = ap.parse_args()

p4 = [x.strip() for x in A.pillars.split(",")]
assert len(p4) == 4, "四柱必须是 4 个字"
START_Y, START_M = map(int, A.start.split("-"))
END_Y, END_M = map(int, A.end.split("-"))
XI_GAN_WX = set(A.xi)
JI_GAN_WX = set(A.ji)
XIZHI = set(A.xi_zhi)
JIZHI = set(A.ji_zhi)

PILLARS = list(zip(["年", "月", "日", "时"], [p[0] for p in p4], [p[1] for p in p4]))
DM = p4[2][0]

DAYUN = []
for item in [x for x in A.dayun.split(",") if x.strip()]:
    ds, gz = item.split(":")
    y, m, d = map(int, ds.split("-"))
    DAYUN.append((date(y, m, d), gz))
DAYUN.sort()

# ---------- 基础表 ----------
GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GAN_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
          "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WX = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

CHONG = dict(zip(ZHI, "午未申酉戌亥子丑寅卯辰巳"))
LIUHE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
         "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
HAI = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
       "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
XING = {frozenset(["子", "卯"]), frozenset(["寅", "巳"]), frozenset(["巳", "申"]),
        frozenset(["寅", "申"]), frozenset(["丑", "戌"]), frozenset(["戌", "未"]),
        frozenset(["未", "丑"]), frozenset(["辰"]), frozenset(["午"]),
        frozenset(["酉"]), frozenset(["亥"])}
SANHUI = [("寅", "卯", "辰"), ("巳", "午", "未"), ("申", "酉", "戌"), ("亥", "子", "丑")]
SANHE = [("申", "子", "辰"), ("亥", "卯", "未"), ("寅", "午", "戌"), ("巳", "酉", "丑")]

YANG = set("甲丙戊庚壬")
DM_YINYANG = "阳" if DM in YANG else "阴"
# 十神：以日主五行 / 阴阳推导
DM_WX = GAN_WX[DM]
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
SAME_YY = {"比肩": 1, "劫财": 0, "食神": 1, "伤官": 0, "偏财": 1, "正财": 0,
           "七杀": 1, "正官": 0, "偏印": 1, "正印": 0}
REL_NAME = {}
for g in GAN:
    gwx = GAN_WX[g]
    gyy = "阳" if g in YANG else "阴"
    same = (gyy == DM_YINYANG)
    if gwx == DM_WX:
        name = "比肩" if same else "劫财"
    elif SHENG[DM_WX] == gwx:
        name = "食神" if same else "伤官"
    elif KE[DM_WX] == gwx:
        name = "偏财" if same else "正财"
    elif KE[gwx] == DM_WX:
        name = "七杀" if same else "正官"
    else:
        name = "偏印" if same else "正印"
    REL_NAME[g] = name

ZHI_CANG = {"子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
            "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
            "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
            "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]}

MZ = [p[2] for p in PILLARS]  # 命局四支


def dy(d):
    name = DAYUN[0][1] if DAYUN else "—"
    for start, n in DAYUN:
        if d >= start:
            name = n
    return name


def rel(zhi):
    """流月支 与 命局四支 的全部关系（通用）"""
    out = []
    for name, g, z in PILLARS:
        if CHONG[zhi] == z:
            out.append("冲%s支%s" % (name, z))
        if LIUHE.get(zhi) == z:
            out.append("合%s支%s" % (name, z))
        if frozenset([zhi, z]) in XING:
            out.append("刑%s支%s" % (name, z) if zhi != z else "自刑%s支%s" % (name, z))
        if HAI[zhi] == z:
            out.append("害%s支%s" % (name, z))
    have = set(MZ) | {zhi}
    # 成局必须由「流月支」参与才算当月变量。
    # 否则原局自身已构成三合/三会的命局（如巳酉丑全），会在每一个月被重复计分，
    # 造成整表系统性偏忌 —— v2 修复（2026-09-30）。
    for grp in SANHUI:
        if zhi in grp and all(x in have for x in grp):
            out.append("%s三会%s局" % ("".join(grp), ZHI_WX[zhi]))
    for grp in SANHE:
        if zhi in grp and all(x in have for x in grp):
            out.append("%s三合%s局" % ("".join(grp), ZHI_WX[grp[1]]))
        elif zhi in grp and sum(1 for x in grp if x in have) == 2:
            other = [x for x in grp if x in have and x != zhi]
            out.append("%s半合%s" % ("".join(sorted([zhi] + other, key=ZHI.index)), ZHI_WX[grp[1]]))
    return "、".join(out) if out else "—"


def tier(gan, zhi):
    """喜忌档：天干五行 + 地支五行 + 成局修正"""
    s = 1 if GAN_WX[gan] in XI_GAN_WX else -1
    if GAN_WX[gan] in JI_GAN_WX:
        s = -1
    if zhi in XIZHI:
        s += 1
    elif zhi in JIZHI:
        s -= 1
    r = rel(zhi)
    for grp in SANHUI + SANHE:
        if ("".join(grp) + "三会%s局" % ZHI_WX[zhi]) in r or ("".join(grp) + "三合%s局" % ZHI_WX[grp[1]]) in r:
            wx = ZHI_WX[zhi] if "三会" in r and ("".join(grp) + "三会") in r else ZHI_WX[grp[1]]
            s += 2 if wx in XI_GAN_WX else -2
    # 半合
    import re
    for m in re.findall(r"半合(.)", r):
        s += 1 if m in XI_GAN_WX else -1
    if s >= 2:
        return "喜", s
    if s == 1:
        return "偏喜", s
    if s == 0:
        return "中", s
    if s == -1:
        return "偏忌", s
    return "忌", s


def motion(zhi):
    r = rel(zhi)
    if any(k in r for k in ("冲", "刑", "害")):
        return "动"
    if "合" in r or "会" in r:
        return "黏"
    return "静"


# ---------- 扫描 ----------
rows = []
d = date(START_Y, START_M, 1)
if END_M == 12:
    end = date(END_Y, 12, 31)
else:
    end = date(END_Y, END_M + 1, 1) - timedelta(days=1)
prev_mg = None
n = 0
while d <= end:
    yg, mg = PP.year_month_gz_of_date(d)
    if mg != prev_mg:
        n += 1
        gan, zhi = mg[0], mg[1]
        t, sc = tier(gan, zhi)
        rows.append({"i": n, "start": d, "yg": yg, "mg": mg,
                     "god": REL_NAME.get(gan, "?"),
                     "wx": GAN_WX.get(gan, "?") + ZHI_WX.get(zhi, "?"),
                     "dy": dy(d), "rel": rel(zhi), "tier": t, "score": sc, "mo": motion(zhi)})
        prev_mg = mg
    d += timedelta(days=1)

# ---------- 输出 ----------
L = []
L.append("# 逐月推演 · 机械计算层")
L.append("")
L.append("> 命局：%s（日主 %s%s）" % (" ".join(p4), DM, DM_YINYANG))
L.append("> 喜神天干五行：%s｜忌神天干五行：%s" % ("".join(sorted(XI_GAN_WX)), "".join(sorted(JI_GAN_WX))))
L.append("> 喜神地支：%s｜忌神地支：%s" % ("".join(x for x in ZHI if x in XIZHI), "".join(x for x in ZHI if x in JIZHI)))
if DAYUN:
    L.append("> 大运：" + "｜".join("%s 起 %s" % (s.strftime("%Y-%m-%d"), g) for s, g in DAYUN))
L.append("> 区间：%d-%02d 至 %d-%02d｜共 %d 个节气月" % (START_Y, START_M, END_Y, END_M, n))
L.append("")
L.append("> ⚠️ **本表只含可机械计算的客观事实：月柱由节气确定，十神与喜忌档由五行生克推出。**")
L.append("> **本表不含任何预测、不含任何事件判断。** 逐月事件断语见《解读层》文档。")
L.append("")
L.append("档位：喜 ≥2 / 偏喜 1 / 中 0 / 偏忌 −1 / 忌 ≤−2（三会或三合成局 ±2，半合 ±1）")
L.append("动静：动=与命局有冲/刑/害；黏=有合或会；静=无关系")
L.append("")

cur = None
for r in rows:
    if r["start"].year != cur:
        cur = r["start"].year
        L.append("")
        L.append("## %d 年（大运 %s）" % (cur, r["dy"]))
        L.append("")
        L.append("| # | 起始 | 月柱 | 十神 | 五行 | 大运 | 与命局关系 | 档 | 动静 |")
        L.append("|---|---|---|---|---|---|---|---|---|")
    L.append("| %d | %s | %s | %s | %s | %s | %s | %s(%+d) | %s |" % (
        r["i"], r["start"].strftime("%m-%d"), r["mg"], r["god"], r["wx"], r["dy"],
        r["rel"], r["tier"], r["score"], r["mo"]))

L.append("")
L.append("---")
L.append("")
L.append("*本表由 `bazi/scripts/monthly_scan_gen.py` 自动生成，可随时重新计算。*")

with open(A.out, "w", encoding="utf-8") as f:
    f.write("\n".join(L))

print("完成：共 %d 个月，输出到 %s" % (n, A.out))
print("日主 %s（%s%s）→ 十神表：" % (DM, DM_WX, DM_YINYANG))
print("  " + "｜".join("%s=%s" % (g, REL_NAME[g]) for g in GAN))
