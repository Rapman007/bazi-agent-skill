# 赛博算命 Skill · 八字排盘与命理分析

> 一个 **Agent Skill**：说一句"算八字"，它就逐步问你要出生信息，跑脚本排盘，然后出一份**结论可被验证**的分析报告。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)

---

## 它能做什么

1. **信息收集** —— 逐步询问姓名、阳历／农历生日、出生时辰、性别、出生地
2. **排盘计算** —— 排四柱、大运、流年、神煞。**全部由脚本计算**（不靠 AI 背万年历，禁止口算）
3. **综合分析** —— 一句话断语 / 总段语 / 逐项注解 / 取象叙事 / 十神方向 / 地形图 / 天气表 / 决策盲区 / 财运专项 / 性格底色 / 断语台账

### 和普通"算命 prompt"的区别

| | |
|---|---|
| **排盘不靠 AI** | 四柱、大运、起运、神煞一律由 Python 脚本输出，AI 不得覆盖 |
| **断语必须可证伪** | 禁止"可能 / 有所波动 / 这是你的课题"这类永远对的话；每条断语都要能被**到期打勾或打叉** |
| **不打档、不排名** | 不给你打"格局高/中/低"。实测证明：拿名人盘和普通人盘同规格排榜**分不开** |
| **只说结构，不说量级** | 回答"你会在哪里摔跤"，不回答"你能跑多快" |
| **神煞、纳音、胎元单开一层** | 常规子平线（格局／旺衰／用神）看不到的层，由"活法层"脚本单独算 |

---

## 安装

> **前提**：这台机器有 Python 3.6+。
> **全部脚本只用标准库 —— 不需要 pip 安装任何东西，不需要联网。**

### 第一步：环境自检（**拷过来先跑这一条**）

```bash
python3 scripts/setup_env.py     # macOS / Linux
python  scripts/setup_env.py     # Windows（python3 常常不存在）
py -3   scripts/setup_env.py     # Windows 备选
```

它检查七项：Python 版本 / **第三方依赖（动态扫描所有脚本的 import）** / 必需文件 /
脚本入口 / 冒烟测试（用示例假盘真跑一遍计算链）/ 输出可写 / 外传体检。

就绪时打印：

```
✅ 环境就绪：拷走即可用，不需要 pip、不需要联网。
   后续所有命令用本机解释器：/usr/bin/python3
```

**照抄最后那一行**，把后文所有 `python3` 换成它。自检没过**不要往下走** ——
缺文件或缺依赖时脚本会**静默降级**（少出神煞、少出五行占比），报告照样生成、看上去齐全，实为残废。

参数：`--json`｜`--fix`（自动补装缺失的第三方包）｜`--quiet`｜`--out 报告.md`。退出码 `0` = 就绪。

### 第二步：放进技能目录

**WorkBuddy**：把整个 `bazi` 文件夹拷到

```
C:\Users\<你的用户名>\.workbuddy\skills\bazi
```

**Claude Code**：

```bash
# 全局（所有项目可用）
git clone https://github.com/Rapman007/bazi-agent-skill ~/.claude/skills/bazi

# 或只装到某个项目（在该 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/Rapman007/bazi-agent-skill .claude/skills/bazi
```

### 第三步：验证

```bash
python3 scripts/setup_env.py --quiet                                   # 一句话结论
python3 scripts/pai_pan.py --solar 1990-05-15 --shichen 午 --sex 男     # 能打出四柱表即成功
```

---

## 依赖与移植

| 项 | 状态 |
|---|---|
| 第三方包 | **0 个**（`setup_env.py` 动态扫描 `scripts/*.py` 的 import 可自证） |
| 联网 | 不需要 |
| Python | 3.6+ |
| 跨平台 | Windows / macOS / Linux（Windows 上注意 `python3` 通常不存在，用 `python` 或 `py -3`） |

**环境清单在 `config/env.json`** —— 最低 Python 版本 / 必需文件 / 入口 / 冒烟用例 / pip 镜像都在里面。
**要改造成自己的 skill，改这一个文件就够**；新增脚本记得同步进 `entrypoints` 与 `local_modules`，
然后重跑 `setup_env.py` 验证。

**一条纪律**：如果自检第 2 项报出第三方依赖，**优先改回标准库，而不是加一条 pip 安装步骤** ——
加依赖 = 每个使用者都得先装包，那就"有痛"了。

---

## 使用

在对话中输入任意关键词触发：

```
算八字  看八字  批八字  排八字  四柱  命盘  算命  排盘  bazi  看运势  命运分析
```

---

## 项目结构

```
bazi-skill/
├── SKILL.md                        # Skill 入口：第〇阶段环境初始化 → 三阶段流程（收信息 / 排盘 / 综合分析）
├── config/
│   └── env.json                    # 环境清单：最低 Python 版本 / 必需文件 / 入口 / 冒烟用例 / pip 镜像
├── scripts/
│   ├── setup_env.py                # 环境自检与调配（**开局先跑这一条**，零依赖）
│   ├── pai_pan.py                  # 四柱／大运／流年排盘（标准库，无 pip 依赖）
│   ├── intake.py                   # 整盘一次喂进：排盘 + 神煞 + 五行 + 调候
│   ├── huofa_layer.py              # 活法层：纳音／胎元／命宫／羊刃／空亡／天乙／三合派生神煞
│   ├── monthly_scan_gen.py         # 逐月推演扫描器（通用版，零依赖）
│   ├── monthly_scan.py             # 旧版逐月扫描（仅存档，勿用于新盘）
│   ├── shensha_engine.py           # 神煞引擎（22 条全跑，直读 references/shensha-table.md）
│   ├── wuxing_engine.py            # 五行力量引擎
│   ├── tiaohou_engine.py           # 调候用神引擎
│   ├── zhi_rel.py                  # 地支关系工具
│   ├── test_pai_pan.py             # 排盘回归测试（22 例）
│   ├── test_engines.py             # 三引擎回归测试（16 例）
│   └── test_intake.py              # 编排器回归测试（12 例）
├── assets/
│   ├── 盘卡模板.md                 # intake.py 的盘卡输入格式
│   └── 盘卡示例.md
├── references/
│   ├── delivery-spec.md            # 交付规格：报告骨架、取象层、已废止清单、对象特别条款
│   ├── falsifiable-protocol.md     # 可证伪断言协议：断语七要素、禁用词黑名单、反事后圆场
│   ├── framework-map.md            # 十线地图：八字／紫微／奇门／六爻／梅花／纳音…的统一坐标系
│   ├── huofa-layer.md              # 活法层读法规格：气 → 象 → 神煞／纳音／胎元
│   ├── shishen-xiang.md            # 十神四问象表（财≠钱、官≠官职、印≠母亲）
│   ├── blunt-mode.md               # 绝对断模式（默认关闭，须使用者明示开启）
│   ├── wuxing-tables.md            # 五行／天干地支／十神／藏干参考表
│   ├── shensha-table.md            # 神煞吉凶与查法
│   ├── shichen-table.md            # 时辰对照表、日上起时法（五鼠遁元）
│   ├── dayun-rules.md              # 大运顺逆排规则、起运年龄计算
│   └── classical-texts.md          # 九本经典典籍核心论命规则摘要
├── README.md
└── LICENSE
```

---

## 参考典籍

| 典籍 | 侧重 |
|---|---|
| 《穷通宝典》 | 日主调候 |
| 《三命通会》 | 格局神煞 |
| 《滴天髓》 | 五行旺衰 |
| 《渊海子平》 | 十神六亲 |
| 《千里命稿》 | 命例实证 |
| 《协纪辨方书》 | 择日神煞 |
| 《果老星宗》 | 星命合参 |
| 《子平真诠》 | 用神格局 |
| 《神峰通考》 | 命理辨误 |

---

## 几条必须知道的边界

1. **八字是"封闭采样"** —— 只有出生时间一个输入。它回答**结构**，不回答**具体哪件事**。想问具体事，应另起占测局（奇门／六爻／梅花），而不是把出生盘反复切片。
2. **定不了高低** —— 成就至少由四个变量决定（时间／时代／家境／选择），八字只提供其中一个。
3. **形貌不出断语** —— 身高、胖瘦、体型、五官、声音，一律不判。
4. **不是科学预测** —— 拿它做人生决策依据会失效。不是"不许"，是"不管用"。

---

## 授权与来源

- **底层项目**：[`jinchenma94/bazi-skill`](https://github.com/jinchenma94/bazi-skill) —— MIT License，Copyright © 2025 jinchenma94
- **本仓库**：在上述基础上二次开发，新增**交付规格**、**可证伪断言协议**、**十线地图**、**活法层**、**十神四问象表**等模块
- **MIT 授权要求保留原版权声明** → `LICENSE` 文件已随仓库保留，**请勿删除**

---

## 免责声明

本项目仅供**传统文化学习与研究**参考，分析结果**不构成任何决策依据**。命理学属传统文化范畴，请理性看待。
