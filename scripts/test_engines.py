#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新引擎回归测试：shensha_engine / wuxing_engine / tiaohou_engine

判据（"活"的标准）：
  ① 同一副盘，多次运行结果稳定
  ② 换副盘，结果随盘变（不是写死）
  ③ 关键已知结果可复现（锚点测试）
  ④ 表被改动时，行为跟着变（真·接线）

运行：python -m pytest test_engines.py -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shensha_engine as SS
import wuxing_engine as WX
import tiaohou_engine as TH

# ⚠️ 以下三盘**全部为编造示例组合**（由随机编造的日期排出），**不对应任何真人命盘**。
#    换盘时只需改这里的三行，其余断言按新盘实跑结果同步。
# 锚点盘：戊土子月（调候丙、甲**双透干**；用于透干/仅藏/全无三态断言）
P_WOMAN = ["甲戌", "丙子", "戊午", "戊午"]
# 泛化盘 A：壬水卯月（与盘 B 日主、月令都不同，用于"换盘即变结果"）
P_A = ["戊辰", "乙卯", "壬戌", "乙巳"]
# 泛化盘 B：戊土寅月
P_B = ["甲子", "丙寅", "戊午", "庚申"]


class TestShensha(unittest.TestCase):

    def test_表能解析出22条(self):
        specs = SS.parse_shensha_block(SS.find_table_path())
        self.assertEqual(len(specs), 22, "神煞表应有 22 条")

    def test_锚点盘_5条且含关键项(self):
        r = SS.compute(P_WOMAN, "女")
        self.assertEqual(len(r["有"]), 5, f"应 5 条，实际 {r['有']}")
        for name in ["将星", "华盖", "羊刃", "灾煞", "空亡"]:
            self.assertIn(name, r["有"], f"应含 {name}")
        # 缺件：两午无驿马、桃花
        for name in ["驿马", "桃花"]:
            self.assertIn(name, r["缺"], f"应缺 {name}")

    def test_锚点盘_将星落午(self):
        """将星：本盘日支午属寅午戌局 → 将星在午，两午命中"""
        r = SS.compute(P_WOMAN, "女")
        mz = next(h for h in r["明细"] if h["name"] == "将星")
        self.assertIn("午", mz["命中"])

    def test_泛化_盘A与盘B结果不同(self):
        ra = SS.compute(P_A, "男")
        rb = SS.compute(P_B, "男")
        self.assertNotEqual(ra["有"], rb["有"], "不同盘应出不同结果")

    def test_泛化_盘B_10条(self):
        """盘B 手工核验过：10 条有"""
        r = SS.compute(P_B, "男")
        expect = {"月德", "文昌", "学堂", "将星", "驿马", "羊刃", "灾煞", "孤辰", "空亡", "血刃"}
        self.assertEqual(set(r["有"]), expect, f"盘B 应有 {expect}，实际 {set(r['有'])}")

    def test_稳定性_多次运行一致(self):
        a = SS.compute(P_WOMAN, "女")
        b = SS.compute(P_WOMAN, "女")
        self.assertEqual(a["有"], b["有"])

    def test_元辰分男女(self):
        """同一盘，男女命元辰结果可能不同（sex_dependent）"""
        m = SS.compute(P_A, "男")
        f = SS.compute(P_A, "女")
        # 至少整表可用、不报错
        self.assertEqual(m["神煞总数"], 22)
        self.assertEqual(f["神煞总数"], 22)


class TestWuxing(unittest.TestCase):

    def test_锚点盘_占比(self):
        r = WX.compute(P_WOMAN)
        pct = r["占比"]
        # 口径：天干1.0 + 藏干按气数归一化
        self.assertAlmostEqual(pct["土"], 42.50, places=2)
        self.assertAlmostEqual(pct["火"], 28.75, places=2)
        self.assertAlmostEqual(pct["木"], 12.50, places=2)
        self.assertAlmostEqual(pct["水"], 12.50, places=2)
        self.assertAlmostEqual(pct["金"], 3.75, places=2)

    def test_总分恒为8(self):
        for p in [P_WOMAN, P_A, P_B]:
            r = WX.compute(p)
            self.assertAlmostEqual(r["总分"], 8.0, places=6)

    def test_两气支按0_6加0_4归一(self):
        """午为两气（丁0.6/己0.4），不能按单气1.0或三气的0.3算"""
        r = WX.compute(P_WOMAN)
        # 土 = 戊(干1.0) + 戊(干1.0) + 戌藏戊0.6 + 午藏己0.4 + 午藏己0.4 = 3.40
        self.assertAlmostEqual(r["计分"]["土"], 3.40, places=2)

    def test_泛化_各盘不同(self):
        a = WX.compute(P_A)["占比"]
        b = WX.compute(P_B)["占比"]
        self.assertNotEqual(a, b)

    def test_透干识别(self):
        r = WX.compute(P_WOMAN)
        self.assertIn("木", r["透干"])   # 甲
        self.assertIn("火", r["透干"])   # 丙
        self.assertIn("土", r["透干"])   # 戊×2
        self.assertIn("金", r["仅藏不透"])  # 辛只藏戌
        self.assertIn("水", r["仅藏不透"])  # 癸只藏子


class TestTiaohou(unittest.TestCase):

    def test_表能解析十干(self):
        t = TH.parse_tiaohou(TH.find_table_path())
        self.assertEqual(len(t), 10, "应有十个天干")
        for g in "甲乙丙丁戊己庚辛壬癸":
            self.assertIn(g, t)
            self.assertEqual(len(t[g]), 12, f"{g} 应有 12 个月")

    def test_锚点盘_戊土子月首用丙(self):
        r = TH.compute(P_WOMAN)
        self.assertEqual(r["日干"], "戊")
        self.assertEqual(r["生月"], "子")
        self.assertEqual(r["主用神"], "丙")

    def test_锚点盘_回盘核对_丙甲双透(self):
        r = TH.compute(P_WOMAN)
        by = {c["用神"]: c for c in r["回盘核对"]}
        self.assertTrue(by["丙"]["本字透干"], "丙应透干")
        self.assertTrue(by["甲"]["本字透干"], "甲应透干")

    def test_泛化_不同盘不同用神(self):
        a = TH.compute(P_A)   # 壬水子月
        b = TH.compute(P_B)   # 戊土寅月
        self.assertEqual(a["主用神"], "戊")
        self.assertEqual(b["主用神"], "丙")
        self.assertNotEqual(a["主用神"], b["主用神"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
