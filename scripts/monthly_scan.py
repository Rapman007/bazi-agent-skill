# -*- coding: utf-8 -*-
"""
逐月推演扫描器（机械计算层）

用途：扫描指定区间内每个"节气月"的月柱、十神、大运、与命局四支的关系及喜忌档。
特点：**只输出可机械计算的客观事实，不做任何解读。**

用法：
    python monthly_scan.py [年柱] [月柱] [日柱] [时柱] [起始年-月] [结束年-月] [输出文件]

默认区间 2026-10 至 2058-12，输出到当前目录 monthly_out.md

⚠️ 本脚本为**旧版**：命局、大运、成局关系、喜忌口径**全部写死**为下方【示例假盘】。
   换人命局请改用 monthly_scan_gen.py（通用版），不要直接改本文件。
"""
import os
import sys
from datetime import date, timedelta

# 零第三方依赖：干支一律走 pai_pan（与排盘同口径）。
# 2026-10-06 起不再依赖 lunar_python。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pai_pan as PP

# ---------- 参数 ----------
# ⚠️ 示例假盘（非真人），仅用于演示。换盘请用 monthly_scan_gen.py。
p4 = (sys.argv[1:5] if len(sys.argv) >= 5 else ["甲子", "丙寅", "戊午", "庚申"])
START_Y, START_M = (2026, 10)
END_Y, END_M = (2058, 12)
OUT = "monthly_out.md"
if len(sys.argv) >= 7:
    sy, sm = sys.argv[5].split("-")
    ey, em = sys.argv[6].split("-")
    START_Y, START_M, END_Y, END_M = int(sy), int(sm), int(ey), int(em)
if len(sys.argv) >= 8:
    OUT = sys.argv[7]

PILLARS = [(n, p[0], p[1]) for n, p in zip(["年", "月", "日", "时"], p4)]
DM = p4[2][0]

# ---------- 基础表 ----------
TEN = {"甲": "食神", "乙": "伤官", "丙": "偏财", "丁": "正财", "戊": "七杀", "己": "正官",
       "庚": "偏印", "辛": "正印", "壬": "比肩", "癸": "劫财"}
WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
      "庚": "金", "辛": "金", "壬": "水", "癸": "水",
      "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
      "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

CHONG = {"子": "午", "丑": "未", "寅": "申", "卯": "酉", "辰": "戌",
         "巳": "亥", "午": "子", "未": "丑", "申": "寅", "酉": "卯",
         "戌": "辰", "亥": "巳"}
LIUHE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
         "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
HAI = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
       "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
XING = {frozenset(["子", "卯"]), frozenset(["寅", "巳"]), frozenset(["巳", "申"]),
        frozenset(["申", "寅"]), frozenset(["丑", "戌"]), frozenset(["戌", "未"]),
        frozenset(["未", "丑"]), frozenset(["辰"]), frozenset(["午"]),
        frozenset(["酉"]), frozenset(["亥"])}

# ⚠️ 示例值：针对示例假盘（四支 子 寅 午 申）预先标注的成局关系 —— 换盘必须重写
GROUP = {
    "辰": ["申子辰三合水局", "子辰半合水"],
    "戌": ["寅午戌三合火局", "午戌半合火"],
    "丑": ["子丑六合"],
    "未": ["午未六合"],
}

# ⚠️ 示例喜忌口径（逐字集合）—— 换盘必须按该盘的用神/忌神重定
XIGAN = set("甲乙丙丁戊己")
JIGAN = set("庚辛壬癸")
XIZHI = set("寅卯巳午未戌")
JIZHI = set("子亥申酉辰")

# ⚠️ 示例大运（假数据，日期与干支均非真人）—— 真实起运日必须由 pai_pan.py 输出后填入
DAYUN = [(date(2028, 1, 1), "乙丑"), (date(2038, 1, 1), "丙寅"),
         (date(2048, 1, 1), "丁卯"), (date(2058, 1, 1), "戊辰")]


def dy(d):
    name = DAYUN[0][1]
    for start, n in DAYUN:
        if d >= start:
            name = n
    return name


def rel(zhi):
    """月支与命局四支的关系"""
    out = []
    for name, g, z in PILLARS:
        if CHONG[zhi] == z:
            out.append("冲%s支%s" % (name, z))
        if LIUHE.get(zhi) == z:
            out.append("合%s支%s" % (name, z))
        if frozenset([zhi, z]) in XING:
            out.append("刑%s支%s" % (name, z))
        if HAI[zhi] == z:
            out.append("害%s支%s" % (name, z))
    out += GROUP.get(zhi, [])
    return "、".join(out) if out else "—"


def tier(gan, zhi):
    """喜忌档：基于用神（火土木燥）与忌神（水金）机械打分"""
    s = 1 if gan in XIGAN else -1
    if zhi in XIZHI:
        s += 1
    elif zhi in JIZHI:
        s -= 1
    r = rel(zhi)
    if "三会水局" in r:
        s -= 2
    elif "半合水" in r:
        s -= 1
    if "半合金" in r:
        s -= 1
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
    if "合" in r:
        return "黏"
    return "静"


# ---------- 扫描 ----------
rows = []
d = date(START_Y, START_M, 1)
end = date(END_Y, END_M, 31)
prev_mg = None
total_days = (end - d).days


def mgof(d):
    return PP.year_month_gz_of_date(d)


n = 0
while d <= end:
    yg, mg = mgof(d)
    if mg != prev_mg:
        n += 1
        gan, zhi = mg[0], mg[1]
        t, sc = tier(gan, zhi)
        rows.append({
            "i": n, "start": d, "yg": yg, "mg": mg,
            "god": TEN.get(gan, "?"), "wx": WX.get(gan, "?") + WX.get(zhi, "?"),
            "dy": dy(d), "rel": rel(zhi), "tier": t, "score": sc, "mo": motion(zhi),
        })
        prev_mg = mg
        if n % 24 == 0:
            print("...已扫描 %d 个月，当前 %s" % (n, d), flush=True)
    d += timedelta(days=1)

# ---------- 输出 ----------
lines = []
lines.append("# 逐月推演 · 机械计算层")
lines.append("")
lines.append("> 命局：%s（日主 %s；喜忌口径见脚本内 XIGAN/XIZHI 常量）" % (" ".join(p4), DM))
lines.append("> 区间：%d-%02d 至 %d-%02d｜共 %d 个节气月" % (START_Y, START_M, END_Y, END_M, n))
lines.append("")
lines.append("> ⚠️ **本表只含可机械计算的客观事实：月柱由节气确定，十神与喜忌档由五行生克推出。**")
lines.append("> **本表不含任何预测、不含任何事件判断。** 逐月事件断语见《解读层》文档。")
lines.append("")
lines.append("档位说明：喜 ≥2 分 / 偏喜 1 分 / 中 0 分 / 偏忌 −1 分 / 忌 ≤−2 分（喜=火土木燥，忌=水金；水金成局额外扣分）")
lines.append("动静说明：动=与命局有冲/刑/害；黏=有合；静=无关系")
lines.append("")

cur_year = None
for r in rows:
    if r["start"].year != cur_year:
        cur_year = r["start"].year
        lines.append("")
        lines.append("## %d 年（大运 %s）" % (cur_year, r["dy"]))
        lines.append("")
        lines.append("| # | 起始 | 月柱 | 十神 | 大运 | 与命局关系 | 档 | 动静 |")
        lines.append("|---|---|---|---|---|---|---|---|")
    lines.append("| %d | %s | %s | %s | %s | %s | %s(%+d) | %s |" % (
        r["i"], r["start"].strftime("%m-%d"), r["mg"], r["god"], r["dy"],
        r["rel"], r["tier"], r["score"], r["mo"]))

lines.append("")
lines.append("---")
lines.append("")
lines.append("*本表由 `bazi/scripts/monthly_scan.py` 自动生成，可随时重新计算。*")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("完成：共 %d 个月，输出到 %s" % (n, OUT))
