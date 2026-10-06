#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行力量引擎（wuxing_engine）—— 按 `references/wuxing-tables.md` §五行力量分布算法 执行

口径（2026-10-04 唯一口径）：
  天干各 1.0 ｜ 地支藏干按"实际气数"归一化到每支 1.0：
    1 气（子卯酉）→ 1.0
    2 气（午亥）  → 0.6 / 0.4
    3 气（其余）  → 0.6 / 0.3 / 0.1
  全盘总分恒为 8.0；占比 = 得分 / 8.0

⚠️ 占比只描述"分布形态"，不等于"力量强弱"。定性因素（月令/透干/有根）须另行判读。

用法：
  python wuxing_engine.py --pillars 甲子,丙寅,戊午,庚申
  python wuxing_engine.py --pillars 甲子,丙寅,戊午,庚申 --json
"""
import argparse
import json

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
WUXING_ORDER = ["木", "火", "土", "金", "水"]

GAN_WX = {c: w for c, w in zip(GAN, "木木火火土土金金水水")}

# 地支藏干（按 本气/中气/余气 顺序），权重按气数归一化
CANG = {
    "子": ["癸"],                    # 1 气
    "丑": ["己", "癸", "辛"],         # 3 气
    "寅": ["甲", "丙", "戊"],         # 3 气
    "卯": ["乙"],                    # 1 气
    "辰": ["戊", "乙", "癸"],         # 3 气
    "巳": ["丙", "庚", "戊"],         # 3 气
    "午": ["丁", "己"],              # 2 气
    "未": ["己", "丁", "乙"],         # 3 气
    "申": ["庚", "壬", "戊"],         # 3 气
    "酉": ["辛"],                    # 1 气
    "戌": ["戊", "辛", "丁"],         # 3 气
    "亥": ["壬", "甲"],              # 2 气
}

# 按气数归一化的权重（每支合计恒为 1.0）
WEIGHT_BY_COUNT = {
    1: [1.0],
    2: [0.6, 0.4],
    3: [0.6, 0.3, 0.1],
}

# 地支本气（供"只看本气"的粗算参考）
ZHI_BENQI = {z: c[0] for z, c in CANG.items()}

# 十二地支的五行归属（粗口径，仅供显示）
ZHI_WX = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}


def compute(pillars):
    """返回五行得分与占比"""
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]

    score = {w: 0.0 for w in WUXING_ORDER}
    detail = {w: [] for w in WUXING_ORDER}

    # 天干 1.0
    for g in gans:
        w = GAN_WX[g]
        score[w] += 1.0
        detail[w].append(f"{g}(干×1.0)")

    # 地支藏干：按气数归一化
    for z in zhis:
        cs = CANG[z]
        ws = WEIGHT_BY_COUNT[len(cs)]
        for j, c in enumerate(cs):
            w = GAN_WX[c]
            wt = ws[j]
            score[w] += wt
            label = "本气" if j == 0 else ("中气" if j == 1 else "余气")
            detail[w].append(f"{z}藏{c}({label}×{wt})")

    total = sum(score.values())
    pct = {w: round(score[w] / total * 100, 2) for w in WUXING_ORDER}

    # 辅助判定：透干 / 仅藏不透
    tougan = sorted({GAN_WX[g] for g in gans}, key=WUXING_ORDER.index)
    cang_only = sorted({GAN_WX[c] for z in zhis for c in CANG[z]} - set(tougan),
                       key=WUXING_ORDER.index)

    return {
        "四柱": pillars,
        "计分": {w: round(score[w], 2) for w in WUXING_ORDER},
        "占比": pct,
        "总分": round(total, 2),
        "透干": tougan,
        "仅藏不透": cang_only,
        "无": [w for w in WUXING_ORDER if score[w] == 0],
        "明细": detail,
    }


def fmt(res):
    out = []
    out.append("【五行力量分布】" + " ".join(res["四柱"]))
    out.append("口径：天干各1.0 ｜ 地支藏干按气数归一化（1气=1.0 / 2气=0.6+0.4 / 3气=0.6+0.3+0.1），总分恒为8.0")
    out.append("")
    out.append(f"{'五行':<4}{'得分':>8}{'占比':>10}   分布")
    for w in sorted(res["占比"], key=lambda x: -res["占比"][x]):
        bar = "█" * int(round(res["占比"][w] / 2))
        out.append(f"{w:<4}{res['计分'][w]:>8.2f}{res['占比'][w]:>9.1f}%   {bar}")
    out.append("")
    out.append(f"透干：{'、'.join(res['透干']) or '无'}")
    out.append(f"仅藏不透：{'、'.join(res['仅藏不透']) or '无'}")
    out.append(f"全无：{'、'.join(res['无']) or '无'}")
    out.append("")
    out.append("—— 得分来源 ——")
    for w in sorted(res["占比"], key=lambda x: -res["占比"][x]):
        if res["明细"][w]:
            out.append(f"· {w}：{' + '.join(res['明细'][w])}")
    out.append("")
    out.append("⚠️ 占比只描述分布形态，不等于力量强弱。月令/透干/有根须另行判读。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="五行力量引擎（口径见 references/wuxing-tables.md）")
    ap.add_argument("--pillars", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ps = [p.strip() for p in args.pillars.replace("，", ",").split(",") if p.strip()]
    if len(ps) != 4:
        ap.error("--pillars 必须给 4 柱")
    res = compute(ps)
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else fmt(res))


if __name__ == "__main__":
    main()
