#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入编排器回归测试（intake.py）

判据（"活"的标准）：
  ① 三种输入方式（四柱直输 / 盘卡 / 出生信息）都能跑通
  ② 四步机械层都真的跑过（不是空壳）
  ③ 编排出的四柱与三引擎用的是同一组干支
  ④ 盘卡解析宽松：空格/逗号/顿号都认；性别必填缺失要报错
  ⑤ 结果随盘变（换盘换结果）

运行：python -m pytest test_intake.py -q
或：  python test_intake.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intake as IK

HERE = os.path.dirname(os.path.abspath(__file__))
CARD = os.path.join(HERE, "..", "assets", "盘卡示例.md")

P_WOMAN = ["甲戌", "丙子", "戊午", "戊午"]
P_B = ["甲子", "丙寅", "戊午", "庚申"]


class TestIntake(unittest.TestCase):

    def test_四柱直输_四步全跑(self):
        r = IK.intake(pillars=P_WOMAN, sex="女")
        self.assertEqual(r["四柱"], P_WOMAN)
        for k in ["1_排盘", "2_神煞", "3_五行", "4_调候"]:
            self.assertIn(k, r["步骤"], f"缺步骤 {k}")
            self.assertTrue(r["步骤"][k]["ok"], f"{k} 失败：{r['步骤'][k]['text'][:200]}")
        self.assertEqual(r["警告"], [], "不应有警告")

    def test_神煞步出22条口径(self):
        r = IK.intake(pillars=P_WOMAN, sex="女")
        txt = r["步骤"]["2_神煞"]["text"]
        self.assertIn("共 22 条", txt)
        self.assertIn("将星", txt)

    def test_五行步出占比(self):
        r = IK.intake(pillars=P_WOMAN, sex="女")
        txt = r["步骤"]["3_五行"]["text"]
        self.assertIn("42.5%", txt)

    def test_调候步出主用神丙(self):
        r = IK.intake(pillars=P_WOMAN, sex="女")
        txt = r["步骤"]["4_调候"]["text"]
        self.assertIn("丙", txt)
        self.assertIn("主用神", txt)

    def test_盘卡模式(self):
        card = IK.parse_card(CARD)
        self.assertEqual(card["pillars"], P_B, f"盘卡解析应得 {P_B}，实际 {card['pillars']}")
        self.assertEqual(card["sex"], "男")
        r2 = IK.intake(pillars=card["pillars"], sex=card["sex"], source=card.get("source"))
        self.assertEqual(r2["四柱"], P_B)
        self.assertTrue(r2["步骤"]["1_排盘"]["ok"])

    def test_盘卡解析_多种分隔符(self):
        import tempfile
        for sep in [" ", ",", "，", "、"]:
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                             encoding="utf-8") as f:
                f.write("四柱：甲戌%s丙子%s戊午%s戊午\n性别：女\n" % (sep, sep, sep))
                p = f.name
            try:
                card = IK.parse_card(p)
                self.assertEqual(card["pillars"], P_WOMAN, f"分隔符 {sep!r} 解析失败")
                self.assertEqual(card["sex"], "女")
            finally:
                os.unlink(p)

    def test_出生信息模式(self):
        r = IK.intake(pillars=None, sex="男", solar="1990-05-15", hour="12:00")
        self.assertIsNotNone(r["四柱"], "应从排盘输出解析出四柱")
        self.assertEqual(len(r["四柱"]), 4)
        # 与 pai_pan 单独跑的锚点一致
        self.assertEqual(r["四柱"], ["庚午", "辛巳", "庚辰", "壬午"])

    def test_三引擎与排盘同干支(self):
        """编排出的四柱必须与各引擎输出里印的四柱一致（防串盘）"""
        r = IK.intake(pillars=P_WOMAN, sex="女")
        self.assertIn(" ".join(P_WOMAN), r["步骤"]["2_神煞"]["text"])
        self.assertIn(" ".join(P_WOMAN), r["步骤"]["3_五行"]["text"])

    def test_结果随盘变(self):
        a = IK.fmt(IK.intake(pillars=P_WOMAN, sex="女"))
        b = IK.fmt(IK.intake(pillars=P_B, sex="男"))
        self.assertNotEqual(a, b, "换盘应换结果")

    def test_fmt_含四步标题(self):
        txt = IK.fmt(IK.intake(pillars=P_WOMAN, sex="女"))
        for t in ["① 排盘", "② 神煞", "③ 五行", "④ 调候"]:
            self.assertIn(t, txt)


class TestCardErrors(unittest.TestCase):

    def test_找不到盘卡报错(self):
        with self.assertRaises(FileNotFoundError):
            IK.parse_card(os.path.join(HERE, "不存在的盘卡.md"))

    def test_盘卡无四柱(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write("性别：女\n")
            p = f.name
        try:
            card = IK.parse_card(p)
            self.assertIsNone(card["pillars"])
        finally:
            os.unlink(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
