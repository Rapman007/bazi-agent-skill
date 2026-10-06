#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活法层计算器（huofa_layer）—— 子平格局看不见的那几层

用途：对**任意**四柱（任何命主，不指向特定个人）计算：
  ① 四柱纳音 + 首尾纳音关系
  ② 胎元（+ 纳音）
  ③ 命宫（需农历月）
  ④ 三合四组派生神煞（驿马/桃花/华盖/将星/劫煞）逐支命中
  ⑤ 空亡（按日柱旬，非按支）
  ⑥ 羊刃（日干）
  ⑦ 天乙贵人（年干 / 日干 两起法）

定位：本脚本只出**客观层**，不含任何解读。
      解读规格见 references/huofa-layer.md；报告写法见 references/delivery-spec.md。

用法：
  python huofa_layer.py --pillars 甲子,丙寅,戊午,庚申
  python huofa_layer.py --pillars 甲子,丙寅,戊午,庚申 --lunar-month 11 --name 某人
"""
import argparse
import sys

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"

# 六十甲子纳音（30 组，两两共用）
NAYIN = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "沙中金", "乙未": "沙中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}

# 三合四组 → 派生神煞（典出《三命通会》，清代改以日支起，本脚本两法都列）
SANHE = {
    "申子辰": {"驿马": "寅", "桃花": "酉", "华盖": "辰", "将星": "子", "劫煞": "巳"},
    "寅午戌": {"驿马": "申", "桃花": "卯", "华盖": "戌", "将星": "午", "劫煞": "亥"},
    "巳酉丑": {"驿马": "亥", "桃花": "午", "华盖": "丑", "将星": "酉", "劫煞": "寅"},
    "亥卯未": {"驿马": "巳", "桃花": "子", "华盖": "未", "将星": "卯", "劫煞": "申"},
}

# 羊刃：阳干取帝旺；阴干各家不一（此处取通行「阴干临官」说，并在输出中标注）
YANGREN_YANG = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
YANGREN_YIN = {"乙": "寅", "丁": "巳", "己": "巳", "辛": "申", "癸": "亥"}

# 天乙贵人（口诀：甲戊庚牛羊 / 乙己鼠猴乡 / 丙丁猪鸡位 / 壬癸兔蛇藏 / 六辛逢马虎）
TIANYI = {
    "甲": "丑未", "戊": "丑未", "庚": "丑未",
    "乙": "子申", "己": "子申",
    "丙": "亥酉", "丁": "亥酉",
    "壬": "卯巳", "癸": "卯巳",
    "辛": "午寅",
}

WUXING_ORDER = "金木水火土"


def nayin_wuxing(name: str) -> str:
    """纳音五行 = 名称末字（海中金→金、覆灯火→火、大驿土→土）"""
    return name[-1]


def sheng_ke(a: str, b: str) -> str:
    """a 对 b 的关系：a 生 b / a 克 b / b 生 a / b 克 a / 同"""
    if a == b:
        return "同"
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if sheng.get(a) == b:
        return "年→时 相生"
    if ke.get(a) == b:
        return "年克时"
    if sheng.get(b) == a:
        return "时→年 相生"
    if ke.get(b) == a:
        return "时克年"
    return "无关"


def taiyuan(month_pillar: str) -> str:
    """胎元 = 月干进一位、月支进三位"""
    g = GAN[(GAN.index(month_pillar[0]) + 1) % 10]
    z = ZHI[(ZHI.index(month_pillar[1]) + 3) % 12]
    return g + z


def minggong(lunar_month: int, hour_zhi: str) -> str:
    """命宫：寅起正月顺数至生月得 A；再自 A 起子时逆数至生时得 B"""
    a = (ZHI.index("寅") + (lunar_month - 1)) % 12
    steps = ZHI.index(hour_zhi)          # 子时为 0 步
    b = (a - steps) % 12
    return ZHI[b]


def kongwang(day_pillar: str):
    """空亡按日柱所在旬（必须用完整干支，不能只拿地支）"""
    g = GAN.index(day_pillar[0])
    z = ZHI.index(day_pillar[1])
    head = (z - g) % 12
    return ZHI[head], ZHI[(head + 10) % 12] + ZHI[(head + 11) % 12]


def parse_pillars(s: str):
    ps = [p.strip() for p in s.replace("，", ",").split(",") if p.strip()]
    if len(ps) != 4:
        raise ValueError("--pillars 必须给 4 柱，逗号分隔，如 甲子,丙寅,戊午,庚申")
    for p in ps:
        if len(p) != 2 or p[0] not in GAN or p[1] not in ZHI:
            raise ValueError(f"非法干支：{p}")
    return ps


def compute(ps, name="", lunar_month=None, hour=None):
    """活法层核心计算。ps 为四柱列表（年,月,日,时），不含任何 IO。

    返回 dict；hour 为出生钟点 (h, m) 时按五鼠遁元校验时柱，不符则写入 __warning。
    """
    gans = [p[0] for p in ps]
    zhis = [p[1] for p in ps]
    nys = [NAYIN[p] for p in ps]
    ny_wx = [nayin_wuxing(n) for n in nys]

    ty = taiyuan(ps[1])
    ty_ny = NAYIN[ty]

    res = {
        "命主": name or "（未命名）",
        "四柱": ps,
        "纳音": {ps[i]: nys[i] for i in range(4)},
        "纳音五行": {ps[i]: ny_wx[i] for i in range(4)},
        "首尾纳音": {
            "年": ny_wx[0], "时": ny_wx[3],
            "是否同五行": ny_wx[0] == ny_wx[3],
            "关系": sheng_ke(ny_wx[0], ny_wx[3]),
        },
        "胎元": {"干支": ty, "纳音": ty_ny, "五行": nayin_wuxing(ty_ny)},
    }

    if lunar_month:
        mg = minggong(lunar_month, zhis[3])
        res["命宫"] = {"支": mg, "农历月": lunar_month}

    # 羊刃
    dg = gans[2]
    if dg in YANGREN_YANG:
        yr, note = YANGREN_YANG[dg], "阳干（取帝旺）"
    else:
        yr, note = YANGREN_YIN[dg], "阴干（取临官·各家有争议）"
    res["羊刃"] = {"日干": dg, "刃支": yr, "取法": note,
                  "四支命中": [z for z in zhis if z == yr]}

    # 空亡
    head, kong = kongwang(ps[2])
    res["空亡"] = {"日柱": ps[2], "所属旬": head + "旬", "空亡支": kong,
                  "四支命中": [z for z in zhis if z in kong]}

    # 天乙贵人
    ty_year = [z for z in TIANYI[gans[0]]]
    ty_day = [z for z in TIANYI[dg]]
    res["天乙贵人"] = {
        "以年干起": {"干": gans[0], "贵支": ty_year, "四支命中": [z for z in zhis if z in ty_year]},
        "以日干起": {"干": dg, "贵支": ty_day, "四支命中": [z for z in zhis if z in ty_day]},
    }

    # 三合四组派生神煞：逐支起，查其余三支
    shensha_scan = {}
    hits = {}
    labels = ["年", "月", "日", "时"]
    for i, base in enumerate(zhis):
        ju = next(k for k in SANHE if base in k)
        found = {k: v for k, v in SANHE[ju].items() if v in zhis}
        shensha_scan[f"{labels[i]}支{base}"] = {"属局": ju, "命中": found}
        for k, v in found.items():
            hits.setdefault(v, set()).add(k)
    summary = {v: sorted(ks) for v, ks in sorted(hits.items(), key=lambda x: ZHI.index(x[0]))}
    res["三合派生神煞"] = {"逐支扫描": shensha_scan, "四支汇总": summary}

    # 缺件：按「每一支各自的局」判该神煞有没有落点（不能按神煞名字一刀切）
    present, absent = set(), set()
    for k in ("驿马", "桃花", "华盖", "将星", "劫煞"):
        if any(SANHE[ju][k] in zhis for ju in {next(x for x in SANHE if z in x) for z in zhis}):
            present.add(k)
        else:
            absent.add(k)
    res["派生神煞_有"] = sorted(present, key=lambda k: ("驿马", "桃花", "华盖", "将星", "劫煞").index(k))
    res["派生神煞_缺"] = sorted(absent, key=lambda k: ("驿马", "桃花", "华盖", "将星", "劫煞").index(k))

    # 五鼠遁元自检：日干 + 时支 应得的时干，与所给时干比对（不擅自改盘，只报警）
    zhi_i = ZHI.index(zhis[3])
    expect_gan = GAN[(ZI_SHI_GAN[GAN.index(gans[2])] + zhi_i) % 10]
    if expect_gan != gans[3]:
        res["__warning"] = (
            "五鼠遁元不符：日干 %s + 时支 %s 应得 %s%s，实际时柱 %s。"
            "（常见原因：日柱写错、或用了非通行的日界口径）"
            % (gans[2], zhis[3], expect_gan, zhis[3], ps[3])
        )
    return res


# 五鼠遁元：日干 -> 子时天干**下标**（与 pai_pan.py 同名表同值，注意此表存下标非字）
ZI_SHI_GAN = {
    0: 0, 5: 0, 1: 2, 6: 2, 2: 4, 7: 4, 3: 6, 8: 6, 4: 8, 9: 8,
}


def format_text(res):
    ps = res["四柱"]
    labels = ["年", "月", "日", "时"]
    dg = res["羊刃"]["日干"]
    out = []
    W = 58
    out.append("=" * W)
    out.append(f"活法层 · {res['命主']}  {' '.join(ps)}")
    out.append("=" * W)
    out.append("【一】四柱纳音")
    for p in ps:
        out.append(f"    {labels[ps.index(p)]}柱 {p}  →  {res['纳音'][p]}（{res['纳音五行'][p]}）")
    s = res["首尾纳音"]
    star = "  ★ 首尾同五行" if s["是否同五行"] else ""
    out.append(f"    首尾：年 {s['年']} ／ 时 {s['时']}{star}   关系：{s['关系']}")
    out.append("")
    out.append("【二】胎元")
    out.append(f"    {res['胎元']['干支']}（{res['胎元']['纳音']} · {res['胎元']['五行']}）")
    if "命宫" in res:
        out.append(f"    命宫：{res['命宫']['支']}（农历{res['命宫']['农历月']}月 + 时支{ps[3][1]}）")
    out.append("")
    out.append("【三】羊刃")
    y = res["羊刃"]
    a = y["四支命中"]
    out.append(f"    {y['日干']}日 · {y['取法']} → 刃在 {y['刃支']}   "
               f"{'✅ 四支命中 ' + str(a) if a else '❌ 四支无'}")
    out.append("")
    out.append("【四】空亡")
    k = res["空亡"]
    a = k["四支命中"]
    out.append(f"    日柱 {k['日柱']} 属 {k['所属旬']} → 空 {k['空亡支']}   "
               f"{'⚠️ 四支命中 ' + str(a) if a else '✅ 全盘无空亡'}")
    out.append("")
    out.append("【五】天乙贵人")
    for key in ("以年干起", "以日干起"):
        d = res["天乙贵人"][key]
        a = d["四支命中"]
        out.append(f"    {key}（{d['干']}）→ 贵支 {d['贵支']}   "
                   f"{'✅ 命中 ' + str(a) if a else '❌ 明处无（可能藏于胎元/命宫）'}")
    out.append("")
    out.append("【六】三合派生神煞（逐支扫描）")
    for kk, vv in res["三合派生神煞"]["逐支扫描"].items():
        got = "、".join(f"{a}={b}" for a, b in vv["命中"].items()) or "无"
        out.append(f"    [{kk} 属{vv['属局']}局]  {got}")
    out.append("    ⇒ 四支汇总：" + ("、".join(
        f"{v}({'/'.join(ks)})" for v, ks in res["三合派生神煞"]["四支汇总"].items()) or "无"))
    out.append("")
    out.append("【七】派生神煞有无（驿马/桃花/华盖/将星/劫煞）")
    out.append("    ✅ 有：" + ("、".join(res["派生神煞_有"]) or "无"))
    out.append("    ❌ 缺：" + ("、".join(res["派生神煞_缺"]) or "无"))
    if res.get("__warning"):
        out.append("")
        out.append("【⚠️ 自检】" + res["__warning"])
    out.append("")
    out.append("说明：本脚本只出客观层，不含解读。解读规格见 references/huofa-layer.md。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="活法层计算器（纳音/胎元/命宫/神煞派生/空亡/羊刃/天乙）")
    ap.add_argument("--pillars", required=True, help="四柱，逗号分隔：年,月,日,时")
    ap.add_argument("--name", default="", help="命主名称（可选）")
    ap.add_argument("--lunar-month", type=int, default=None, help="农历月（1-12），给了才算命宫")
    ap.add_argument("--hour", help="出生钟点 HH:MM（可选，用于五鼠遁元自检时柱）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    try:
        ps = parse_pillars(args.pillars)
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(2)

    hour = None
    if args.hour:
        try:
            hh, mm = args.hour.split(":")
            hour = (int(hh), int(mm))
        except ValueError:
            print("[错误] --hour 需要 HH:MM", file=sys.stderr)
            sys.exit(2)

    res = compute(ps, name=args.name, lunar_month=args.lunar_month, hour=hour)

    if args.json:
        import json
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    print(format_text(res))


if __name__ == "__main__":
    main()
