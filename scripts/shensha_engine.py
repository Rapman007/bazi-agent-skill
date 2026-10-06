#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神煞引擎（shensha_engine）—— 直接解析 `references/shensha-table.md` 的机器可读块

设计原则（2026-10-04 接线）：
  **表是唯一口径，代码不含任何口诀。** 改表即改行为。
  本脚本只做三件事：① 解析 md 里的 yaml 块 ② 按 anchor/mode 求值 ③ 输出命中。

用途：
  python shensha_engine.py --pillars 甲子,丙寅,戊午,庚申 --sex 女
  python shensha_engine.py --pillars 甲子,丙寅,戊午,庚申 --sex 女 --json

口径：全 22 条神煞；两法（年支/日支）并集输出并标来源；时柱未知时不凑时支。
"""
import argparse
import json
import os
import re
import sys

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
YANG_GAN = set("甲丙戊庚壬")

# 三合局（用于 mode: sanhe 的落点局判定）
SANHE_GROUPS = ["申子辰", "寅午戌", "巳酉丑", "亥卯未"]
# 孤辰/寡宿用的三支组
TRIO_GROUPS = ["亥子丑", "寅卯辰", "巳午未", "申酉戌"]


# ---------------------------------------------------------------- 表解析

def find_table_path():
    """定位 shensha-table.md（相对本脚本或 cwd）"""
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, "..", "references", "shensha-table.md"),
        os.path.join(here, "references", "shensha-table.md"),
        os.path.join(os.getcwd(), "references", "shensha-table.md"),
        os.path.join(os.getcwd(), "shensha-table.md"),
    ]
    for c in cands:
        if os.path.isfile(c):
            return os.path.normpath(c)
    raise FileNotFoundError("找不到 shensha-table.md，请确认 references/ 与 scripts/ 同级")


def parse_shensha_block(md_path):
    """抽取 ```yaml shensha: ... ``` 块，做**零依赖**极简 YAML 解析。

    只支持本表实际用到的结构：list of dict / 嵌套 dict / list 值 / 行内 dict。
    不引入 pyyaml，保持脚本自足（可在断网/纯净环境跑）。
    """
    txt = open(md_path, encoding="utf-8").read()
    m = re.search(r"```yaml\s*\nshensha:\s*\n(.*?)\n```", txt, re.S)
    if not m:
        raise ValueError("未找到 yaml shensha 块")
    body = m.group(1)
    lines = body.split("\n")

    items = []
    cur = None
    key_stack = []          # [(缩进, key)] 用于嵌套 dict

    def strip_comment(s):
        # 只去行尾注释（避免误伤引号内的 #，本表无此情形）
        i = s.find(" #")
        return s[:i] if i >= 0 else s

    def parse_scalar(v):
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            if not inner:
                return []
            return [parse_scalar(x) for x in inner.split(",")]
        if v.startswith("{") and v.endswith("}"):
            inner = v[1:-1].strip()
            d = {}
            for part in inner.split(","):
                if ":" in part:
                    k, _, val = part.partition(":")
                    d[k.strip()] = parse_scalar(val)
            return d
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        if v in ("true", "false"):
            return v == "true"
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        return v

    def indent_of(s):
        return len(s) - len(s.lstrip(" "))

    for raw in lines:
        if not raw.strip():
            continue
        raw = strip_comment(raw.rstrip())
        if not raw.strip():
            continue
        ind = indent_of(raw)
        line = raw.strip()

        if line.startswith("- "):
            # 新条目
            cur = {}
            items.append(cur)
            key_stack = []
            rest = line[2:].strip()
            if rest:
                k, _, v = rest.partition(":")
                cur[k.strip()] = parse_scalar(v)
            continue

        if cur is None:
            continue

        # 弹出比当前缩进深的栈
        while key_stack and key_stack[-1][0] >= ind:
            key_stack.pop()

        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        v_nc = strip_comment(v).strip()

        if v_nc == "":
            # 开新嵌套层——先看下一层是 list 还是 dict，这里统一建 dict，遇 list 再转
            node = {}
            target = cur
            for _, kk in key_stack:
                target = target[kk]
            target[k] = node
            key_stack.append((ind, k))
        else:
            target = cur
            for _, kk in key_stack:
                target = target[kk]
            target[k] = parse_scalar(v_nc)

    return items


def normalize_map(m):
    """把 list 值统一成 list（YAML 解析后可能是标量）"""
    out = {}
    for k, v in m.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
        elif isinstance(v, dict):
            out[str(k)] = {str(kk): ([str(x) for x in vv] if isinstance(vv, list) else [str(vv)])
                           for kk, vv in v.items()}
        else:
            out[str(k)] = [str(v)]
    return out


# ---------------------------------------------------------------- 求值

def ju_of(zhi, groups):
    """给定地支，返回其所属的（三合/三支）局"""
    for g in groups:
        if zhi in g:
            return g
    return None


def anchors_of(spec, pillars, sex, year_gan_is_yang):
    """按 anchor 取出锚点值列表"""
    yg, yz, mg, mz, dg, dz, hg, hz = split_pillars(pillars)
    a = spec["anchor"]
    if a == "year_gan":
        return [yg]
    if a == "day_gan":
        return [dg]
    if a == "month_zhi":
        return [mz]
    if a == "year_zhi":
        return [yz]
    if a == "day_zhi":
        return [dz]
    if a == "day_pillar":
        return [dg + dz]
    if a == "year_gan+day_gan":
        return [yg, dg]
    if a == "year_zhi+day_zhi":
        return [yz, dz]
    raise ValueError(f"未知 anchor: {a}")


def split_pillars(pillars):
    g = [p[0] for p in pillars]
    z = [p[1] for p in pillars]
    return g[0], z[0], g[1], z[1], g[2], z[2], g[3], z[3]


def resolve_targets(spec, anchors):
    """由锚点值求落点集合（set）。返回 [(锚点值, [落点...]), ...]"""
    mode = spec["mode"]
    m = normalize_map(spec.get("map") or {})
    out = []

    if mode == "direct":
        for anc in anchors:
            if spec.get("sex_dependent"):
                # 元辰：map 是 {性别组: {支: [支]}}
                grp = "阳年男/阴年女" if _first_group_applies(anc) else "阴年男/阳年女"
                sub = m.get(grp, {})
                out.append((anc, sub.get(anc, [])))
            else:
                out.append((anc, m.get(anc, [])))
        return out

    if mode == "sanhe":
        for anc in anchors:
            # 依次尝试：三合局 key、三支组 key —— 取 map 中真实存在的那个
            # （不能只取第一个非 None 的局，否则「孤辰」这类三支组神煞会被三合局误吞）
            hit = None
            for groups in (SANHE_GROUPS, TRIO_GROUPS):
                g = ju_of(anc, groups)
                if g is not None and g in m:
                    hit = m[g]
                    break
            out.append((anc, hit or []))
        return out

    if mode == "offset":
        off = (spec.get("map") or {}).get("offset", -1)
        if isinstance(off, dict):
            off = off.get("offset", -1)
        for anc in anchors:
            i = ZHI.index(anc)
            out.append((anc, [ZHI[(i + off) % 12]]))
        return out

    if mode == "xun":
        for anc in anchors:                       # anc 是日柱干支
            g, z = GAN.index(anc[0]), ZHI.index(anc[1])
            head = ZHI[(z - g) % 12]              # 旬首地支
            key = GAN[0] + head                   # 甲X
            out.append((anc, m.get(key, [])))
        return out

    raise ValueError(f"未知 mode: {mode}")


_SEX_CTX = {"sex": None, "yang_year": False}


def _first_group_applies(_anc):
    """元辰用：判断该用第一表（阳年男/阴年女）还是第二表"""
    sex, yang_year = _SEX_CTX["sex"], _SEX_CTX["yang_year"]
    return (yang_year and sex == "男") or ((not yang_year) and sex == "女")


def compute(pillars, sex="男"):
    """核心：返回全部命中神煞"""
    yg, yz, mg, mz, dg, dz, hg, hz = split_pillars(pillars)
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    yang_year = yg in YANG_GAN
    _SEX_CTX["sex"] = sex
    _SEX_CTX["yang_year"] = yang_year

    spec_path = find_table_path()
    specs = parse_shensha_block(spec_path)

    hits = []
    for spec in specs:
        name = spec["name"]
        target_layer = spec.get("target", "zhi")

        anchors = anchors_of(spec, pillars, sex, yang_year)
        pairs = resolve_targets(spec, anchors)

        # 落点候选：按 target 层
        if target_layer == "gan":
            cand = list(gans)
            layer_cn = "天干"
        elif target_layer == "zhi":
            cand = list(zhis)
            layer_cn = "地支"
        elif target_layer == "zhi_no_year":
            cand = zhis[1:]
            layer_cn = "月日时支"
        elif target_layer == "mixed":
            cand = list(gans) + list(zhis)
            layer_cn = "天干或地支"
        else:
            cand = list(zhis)
            layer_cn = "地支"

        found = {}   # 落点字 -> [来源锚点]
        for anc, targets in pairs:
            for t in targets:
                if t in cand:
                    found.setdefault(t, []).append(anc)

        if found:
            hits.append({
                "name": name,
                "alias": spec.get("alias"),
                "jx": spec.get("jx"),
                "anchor": spec["anchor"],
                "mode": spec["mode"],
                "target_layer": layer_cn,
                "命中": {k: sorted(set(v)) for k, v in sorted(
                    found.items(), key=lambda x: (GAN.index(x[0]) if x[0] in GAN else 100, ZHI.index(x[0]) if x[0] in ZHI else 100))},
            })

    present = [h["name"] for h in hits]
    absent = [s["name"] for s in specs if s["name"] not in present]
    return {
        "四柱": pillars,
        "性别": sex,
        "神煞总数": len(specs),
        "有": present,
        "缺": absent,
        "明细": hits,
        "表文件": spec_path,
    }


# ---------------------------------------------------------------- 输出

def fmt(res):
    out = []
    out.append("【神煞引擎】四柱 " + " ".join(res["四柱"]) + f" · {res['性别']}命")
    out.append(f"口径表：{res['表文件']}（共 {res['神煞总数']} 条）")
    out.append("")
    out.append(f"✅ 有（{len(res['有'])}）：" + ("、".join(res["有"]) or "无"))
    out.append(f"❌ 缺（{len(res['缺'])}）：" + ("、".join(res["缺"]) or "无"))
    out.append("")
    out.append("—— 命中明细 ——")
    for h in res["明细"]:
        jx = h["jx"] or ""
        al = f"（{h['alias']}）" if h.get("alias") else ""
        out.append(f"· {h['name']}{al} [{jx}]  落{h['target_layer']}")
        for z, srcs in h["命中"].items():
            out.append(f"    {z}  ← 起自 {'/'.join(srcs)}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="神煞引擎（读 references/shensha-table.md）")
    ap.add_argument("--pillars", required=True, help="四柱，逗号分隔，如 甲子,丙寅,戊午,庚申")
    ap.add_argument("--sex", default="男", choices=["男", "女"])
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    ps = [p.strip() for p in args.pillars.replace("，", ",").split(",") if p.strip()]
    if len(ps) != 4:
        ap.error("--pillars 必须给 4 柱")

    res = compute(ps, args.sex)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(fmt(res))


if __name__ == "__main__":
    main()
