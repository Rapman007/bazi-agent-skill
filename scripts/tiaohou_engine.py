#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调候用神引擎（tiaohou_engine）—— 解析 `references/tiaohou-table.md` 的机器可读块

口径：《穷通宝典》逐月调候用神。第一个为主用神，其后为次选/辅佐。
⚠️ 调候是"药"，不是"格局"；调候 ≠ 喜用神（后者还含扶抑/通关）。

用法：
  python tiaohou_engine.py --pillars 甲子,丙寅,戊午,庚申
  python tiaohou_engine.py --pillars 甲子,丙寅,戊午,庚申 --json
"""
import argparse
import json
import os
import re

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GAN_WX = {c: w for c, w in zip(GAN, "木木火火土土金金水水")}


def find_table_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in [os.path.join(here, "..", "references", "tiaohou-table.md"),
              os.path.join(here, "references", "tiaohou-table.md"),
              os.path.join(os.getcwd(), "references", "tiaohou-table.md")]:
        if os.path.isfile(c):
            return os.path.normpath(c)
    raise FileNotFoundError("找不到 tiaohou-table.md")


def parse_tiaohou(md_path):
    """解析 ```yaml tiaohou: ...``` 块（每行一个天干，值为 {月支: [用神]}）"""
    txt = open(md_path, encoding="utf-8").read()
    m = re.search(r"```yaml\s*\ntiaohou:\s*\n(.*?)\n```", txt, re.S)
    if not m:
        raise ValueError("未找到 yaml tiaohou 块")
    out = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        gan, _, rest = line.partition(":")
        gan = gan.strip()
        rest = rest.strip()
        if not rest.startswith("{"):
            continue
        inner = rest[1:-1].strip()
        month_map = {}
        # 按 "月支: [..]" 切分（用正则稳妥）
        for mm in re.finditer(r"([子丑寅卯辰巳午未申酉戌亥])\s*:\s*\[([^\]]*)\]", inner):
            mz = mm.group(1)
            vals = [x.strip() for x in mm.group(2).split(",") if x.strip()]
            month_map[mz] = vals
        out[gan] = month_map
    return out


def compute(pillars):
    """返回调候用神 + 回盘核对"""
    day_gan, month_zhi = pillars[2][0], pillars[1][1]
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]

    table = parse_tiaohou(find_table_path())
    if day_gan not in table:
        raise ValueError(f"表中无此日干：{day_gan}")
    ushen = table[day_gan].get(month_zhi)
    if ushen is None:
        raise ValueError(f"表中无此月支：{month_zhi}")

    # 回盘核对：每个用神字 是否透干 / 是否只藏 / 是否全无
    check = []
    for u in ushen:
        wx = GAN_WX[u]
        in_gan = u in gans                      # 用神本字透干
        # 藏干中含同五行者
        from_same_wx = [g for g in gans if GAN_WX[g] == wx]
        check.append({
            "用神": u,
            "五行": wx,
            "本字透干": in_gan,
            "同五行透干": sorted(set(from_same_wx)),
            "在四支": [z for z in zhis if u in [c for c in _cang(z)]],
            "状态": "✅ 本字透干" if in_gan else (
                "🟡 同五行透干（非本字）" if from_same_wx else
                ("🟡 仅藏于支" if any(u in _cang(z) for z in zhis) else "❌ 全无")),
        })

    return {
        "四柱": pillars,
        "日干": day_gan,
        "生月": month_zhi,
        "主用神": ushen[0],
        "全部用神": ushen,
        "回盘核对": check,
        "表文件": find_table_path(),
    }


_CANG_TBL = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"], "午": ["丁", "己"],
    "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"], "酉": ["辛"],
    "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}


def _cang(z):
    return _CANG_TBL.get(z, [])


def fmt(res):
    out = []
    out.append("【调候用神】" + " ".join(res["四柱"]))
    out.append(f"日干 {res['日干']} · 生{res['生月']}月　⇒　主用神：**{res['主用神']}**")
    out.append(f"全部用神（按先后）：{' / '.join(res['全部用神'])}")
    out.append("")
    out.append("—— 回盘核对 ——")
    for c in res["回盘核对"]:
        out.append(f"· {c['用神']}（{c['五行']}）　{c['状态']}")
        if c["同五行透干"]:
            out.append(f"      同五行透干：{'、'.join(c['同五行透干'])}")
        if c["在四支"]:
            out.append(f"      见于地支：{'、'.join(c['在四支'])}")
    out.append("")
    out.append("⚠️ 调候是\"药\"不是\"格局\"；调候 ≠ 喜用神。有药 ≠ 药有效（须看透干/有根/被克）。")
    out.append(f"口径表：{res['表文件']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="调候用神引擎（口径见 references/tiaohou-table.md）")
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
