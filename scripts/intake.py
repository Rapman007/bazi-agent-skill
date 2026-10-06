#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入编排器（intake）—— 把"已经排好的整盘材料"一次吃进来，一次跑完四步。

用户场景（2026-10-04 立）：
  手上有一份别处排好/已经编排好的盘（四柱 + 性别，可能还带出生信息），
  不想一步步走交互式采集，希望**直接输入、直接出机械层**。

本脚本只做"编排"：它自己不算任何口径，而是依次调用四个引擎
（pai_pan / shensha_engine / wuxing_engine / tiaohou_engine），
把结果拼成一份**机械层报告**，供上层写解读。

用法（三种输入方式任选）：
  ① 命令行直接给四柱
     python intake.py --pillars 甲子,丙寅,戊午,庚申 --sex 女

  ② 给一个"盘卡"文件（见 assets/盘卡模板.md）
     python intake.py --card 我的盘.md

  ③ 只给出生信息，让 pai_pan 自己推四柱
     python intake.py --solar 1990-05-15 --hour 12:00 --sex 男

选项：
  --json      机械层以 JSON 输出（供程序消费）
  --out FILE  把机械层写入文件（默认打印到 stdout）
  --quiet     只打印汇总行

⚠️ 本脚本**不做解读、不出断语**。它只把"客观层"摆齐。
   断语与报告见 references/delivery-spec.md。
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"


# ---------------------------------------------------------------- 盘卡解析

def parse_card(path):
    """解析盘卡（markdown 或纯文本）。返回 dict。

    支持的写法（宽松，只要含四柱即可）：
      - 四柱：甲子 丙寅 戊午 庚申        （或逗号/顿号分隔）
      - 性别：女
      - 来源：原文直给
      - 出生：1990-05-15 12:00           （可选）
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("找不到盘卡文件：%s" % path)
    txt = open(path, encoding="utf-8").read()

    out = {"pillars": None, "sex": None, "source": None, "birth": None}

    # 四柱：先找"四柱"标签行，找不到就在全文里搜 4 组连续的干支
    m = re.search(r"四柱\s*[：:]\s*([^\n]+)", txt)
    cand_line = m.group(1) if m else txt
    parts = re.split(r"[\s,，、|]+", cand_line.strip())
    gz = [p for p in parts if len(p) == 2 and p[0] in GAN and p[1] in ZHI]
    if len(gz) >= 4:
        out["pillars"] = gz[:4]

    m = re.search(r"性别\s*[：:]\s*([男女])", txt)
    if m:
        out["sex"] = m.group(1)

    m = re.search(r"来源\s*[：:]\s*([^\n]+)", txt)
    if m:
        out["source"] = m.group(1).strip()

    m = re.search(r"出生\s*[：:]\s*([^\n]+)", txt)
    if m:
        out["birth"] = m.group(1).strip()

    return out


# ---------------------------------------------------------------- 引擎调用

def run_engine(script, args):
    """跑一个引擎脚本，返回 stdout 文本（失败则带错误返回）"""
    p = subprocess.run(
        [PY, os.path.join(HERE, script)] + args,
        capture_output=True, text=True, encoding="utf-8",
    )
    if p.returncode != 0:
        return {"ok": False, "text": (p.stdout or "") + (p.stderr or "")}
    return {"ok": True, "text": p.stdout}


def run_json(script, args):
    """跑一个引擎并取 JSON（引擎需支持 --json）"""
    p = subprocess.run(
        [PY, os.path.join(HERE, script)] + args + ["--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


# ---------------------------------------------------------------- 主流程

def intake(pillars=None, sex="男", source=None, solar=None, hour=None,
           shichen=None, place=None, lunar=None):
    """编排：出机械层。返回 dict。"""
    result = {"四柱": None, "性别": sex, "来源": source, "步骤": {}, "警告": []}

    # ---- 第 1 步：pai_pan ------------------------------------------------
    if pillars:
        pp_args = ["--pillars", ",".join(pillars), "--sex", sex]
        if source:
            pp_args += ["--source", source]
    elif solar or lunar:
        pp_args = ["--sex", sex]
        if solar:
            pp_args += ["--solar", solar]
        if lunar:
            pp_args += ["--lunar", lunar]
        if hour:
            pp_args += ["--hour", hour]
        elif shichen:
            pp_args += ["--shichen", shichen]
        if place:
            pp_args += ["--place", place]
    else:
        raise ValueError("必须给 --pillars / --card / --solar / --lunar 之一")

    pp = run_engine("pai_pan.py", pp_args)
    result["步骤"]["1_排盘"] = {"ok": pp["ok"], "text": pp["text"]}
    if not pp["ok"]:
        result["警告"].append("排盘失败，后续步骤中止")
        return result

    # 从 pai_pan 输出里抓四柱（保证三引擎用同一组干支）
    if pillars is None:
        m = re.search(r"\| 天干 \| (\S+) \| (\S+) \| (\S+) \| (\S+) \|", pp["text"])
        n = re.search(r"\| 地支 \| (\S+) \| (\S+) \| (\S+) \| (\S+) \|", pp["text"])
        if not (m and n):
            result["警告"].append("无法从排盘输出解析四柱，后续步骤中止")
            return result
        pillars = [m.group(i) + n.group(i) for i in range(1, 5)]
    result["四柱"] = pillars
    pillar_str = ",".join(pillars)

    # ---- 第 2 步：神煞（22 条） -------------------------------------------
    ss = run_engine("shensha_engine.py", ["--pillars", pillar_str, "--sex", sex])
    result["步骤"]["2_神煞"] = {"ok": ss["ok"], "text": ss["text"]}
    if not ss["ok"]:
        result["警告"].append("神煞引擎失败")

    # ---- 第 3 步：五行力量 -------------------------------------------------
    wx = run_engine("wuxing_engine.py", ["--pillars", pillar_str])
    result["步骤"]["3_五行"] = {"ok": wx["ok"], "text": wx["text"]}
    if not wx["ok"]:
        result["警告"].append("五行引擎失败")

    # ---- 第 4 步：调候用神 -------------------------------------------------
    th = run_engine("tiaohou_engine.py", ["--pillars", pillar_str])
    result["步骤"]["4_调候"] = {"ok": th["ok"], "text": th["text"]}
    if not th["ok"]:
        result["警告"].append("调候引擎失败")

    return result


def fmt(res):
    out = []
    out.append("# 机械层（intake 编排）")
    out.append("")
    out.append("- 四柱：%s" % (" ".join(res["四柱"]) if res["四柱"] else "（未解析）"))
    out.append("- 性别：%s" % res["性别"])
    if res.get("来源"):
        out.append("- 来源：%s" % res["来源"])
    out.append("")
    order = ["1_排盘", "2_神煞", "3_五行", "4_调候"]
    titles = {"1_排盘": "① 排盘（pai_pan.py）", "2_神煞": "② 神煞 22 条（shensha_engine.py）",
              "3_五行": "③ 五行力量（wuxing_engine.py）", "4_调候": "④ 调候用神（tiaohou_engine.py）"}
    for k in order:
        step = res["步骤"].get(k)
        if not step:
            continue
        out.append("---")
        out.append("")
        out.append("## " + titles[k])
        out.append("")
        out.append(step["text"].rstrip())
        out.append("")
    if res["警告"]:
        out.append("---")
        out.append("")
        out.append("## ⚠️ 警告")
        for w in res["警告"]:
            out.append("- " + w)
        out.append("")
    out.append("---")
    out.append("")
    out.append("> 本文件只含**客观层**，不含解读。断语与报告规格见 `references/delivery-spec.md`。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="输入编排器：盘卡/四柱/出生信息 → 机械层")
    ap.add_argument("--pillars", help="四柱，逗号分隔，如 甲子,丙寅,戊午,庚申")
    ap.add_argument("--card", help="盘卡文件路径（见 assets/盘卡模板.md）")
    ap.add_argument("--solar", help="阳历 YYYY-MM-DD（走出生信息模式）")
    ap.add_argument("--lunar", help="农历 YYYY-MM-DD（走出生信息模式）")
    ap.add_argument("--hour", help="出生钟点 HH:MM")
    ap.add_argument("--shichen", choices=list(ZHI), help="时辰地支")
    ap.add_argument("--place", help="出生地")
    ap.add_argument("--sex", choices=["男", "女"], default=None)
    ap.add_argument("--source", help="四柱来源备注")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--out", help="写入文件（默认 stdout）")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    card = {}
    if args.card:
        card = parse_card(args.card)

    pillars = None
    if args.pillars:
        norm = args.pillars.replace("，", ",").replace("、", ",")
        pillars = [p.strip() for p in norm.split(",") if p.strip()]
    elif card.get("pillars"):
        pillars = card["pillars"]

    sex = args.sex or card.get("sex")
    if not sex:
        print("[错误] 未指定性别：请给 --sex 男/女，或在盘卡里写「性别：女」", file=sys.stderr)
        return 2

    source = args.source or card.get("source")

    res = intake(
        pillars=pillars, sex=sex, source=source,
        solar=args.solar, hour=args.hour, shichen=args.shichen,
        place=args.place, lunar=args.lunar,
    )

    text = json.dumps(res, ensure_ascii=False, indent=2) if args.as_json else fmt(res)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        if not args.quiet:
            print("已写入：%s" % args.out)
            print("四柱：%s" % (" ".join(res["四柱"]) if res["四柱"] else "（未解析）"))
    else:
        print(text)

    return 0 if not res["警告"] else 1


if __name__ == "__main__":
    sys.exit(main())
