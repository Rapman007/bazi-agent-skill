#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境自检与调配（setup_env）· bazi skill 开局第一条

用途：把这个 skill 拷到任何一台机器后，**先跑这一条**，它会告诉你
      这台机器能不能跑、缺什么、以及缺的那一样用什么命令补。

检查六个环节（全部只用标准库，自己零依赖）：
  1. Python 版本（读 config/env.json 的 min_version）
  2. 第三方依赖 —— **动态扫描** scripts/*.py 的 import，凡非标准库即报出
  3. 必需文件完整性（SKILL.md / references / assets / config）
  4. 脚本入口可运行性（逐个 --help）
  5. 冒烟测试（用**示例假盘**真跑一遍计算链，核对关键输出段）
  6. 输出目录可写

设计目标：**无痛用上**。本 skill 的常态是「零第三方依赖」——
拷走即可用，不需要 pip、不需要联网。若第 2 项报警，说明有脚本引入了外部包，
此时要么改回标准库，要么用 --fix 补装（须有网）。

用法：
    python scripts/setup_env.py            # 自检 + 报告
    python scripts/setup_env.py --json     # 结构化输出
    python scripts/setup_env.py --fix      # 自检并尝试自动补装缺失的第三方包
    python scripts/setup_env.py --quiet    # 只输出结论行
    python scripts/setup_env.py --out 环境报告.md

退出码：0 = 环境就绪；1 = 有未通过项。
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(ROOT, "config", "env.json")

# 标准库兜底表（Python 3.10+ 用 sys.stdlib_module_names，更低版本用这张表）
_STDLIB_FALLBACK = set("""
abc aifc argparse array ast asyncio base64 bdb binascii bisect builtins bz2
cProfile calendar cmath cmd code codecs codeop collections colorsys compileall
concurrent configparser contextlib copy copyreg csv ctypes curses datetime dbm
decimal difflib dis distutils doctest email encodings ensurepip enum errno
faulthandler fcntl filecmp fileinput fnmatch formatter fractions ftplib functools
gc getopt getpass gettext glob grp gzip hashlib heapq hmac html http imaplib
importlib imp inspect io ipaddress itertools json keyword linecache locale logging
lzma mailbox marshal math mimetypes mmap modulefinder msvcrt multiprocessing netrc
nis nntplib numbers operator optparse os ossaudiodev pathlib pdb pickle
pickletools pipes pkgutil platform plistlib poplib posix pprint profile pstats
pty pwd py_compile pyclbr pydoc queue quopri random re readline reprlib resource
rlcompleter runpy sched secrets select selectors shelve shlex shutil signal site
smtpd smtplib sndhdr socket socketserver sqlite3 ssl stat statistics string
stringprep struct subprocess symtable sys sysconfig syslog tabnanny tarfile
telnetlib tempfile termios textwrap threading time timeit tkinter token tokenize
trace traceback tracemalloc tty turtle types typing unicodedata unittest urllib
uu uuid venv warnings wave weakref webbrowser winreg winsound wsgiref xdrlib xml
xmlrpc zipapp zipfile zipimport zlib
""".split())

try:
    STDLIB = set(sys.stdlib_module_names)
except AttributeError:
    STDLIB = _STDLIB_FALLBACK

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_\.]*)", re.M)


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def _p(s=""):
    """安全打印：控制台编码兜不住 emoji 时自动降级，不让脚本崩在打印上。"""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        out = s.encode(enc, "replace").decode(enc, "replace")
    except Exception:
        out = s
    try:
        sys.stdout.write(out + "\n")
    except Exception:
        sys.stdout.write(re.sub(r"[^\x00-\x7f]", "?", s) + "\n")


# ---------------------------------------------------------------------------
# 单项检查
# ---------------------------------------------------------------------------
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_version(text):
    nums = re.findall(r"\d+", text)
    return tuple(int(x) for x in nums[:3]) if nums else (0,)


def check_python(cfg):
    want = cfg.get("python", {}).get("min_version", "3.6")
    have = "%d.%d.%d" % sys.version_info[:3]
    passed = parse_version(have) >= parse_version(want)
    detail = "本机 %s，要求 ≥ %s" % (have, want)
    if not passed:
        return {
            "level": "fail", "title": "Python 版本",
            "detail": detail,
            "fix": "装一个 ≥ %s 的 Python（https://www.python.org/downloads/），再重跑本条" % want,
        }
    return {"level": "ok", "title": "Python 版本", "detail": detail}


def scan_third_party(cfg):
    """动态扫描：凡 import 的不是标准库、也不是本目录模块，就记为第三方依赖。"""
    local = set(cfg.get("local_modules", []))
    skip_dirs = {"config", "references", "assets"}
    found = {}
    scanned = 0
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py"):
            continue
        scanned += 1
        path = os.path.join(HERE, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
        except Exception:
            continue
        for mod in IMPORT_RE.findall(src):
            top = mod.split(".")[0]
            if top in local or top in STDLIB or top.startswith("_"):
                continue
            found.setdefault(top, set()).add(fn)
    _ = skip_dirs
    return scanned, found


def check_third_party(cfg):
    scanned, found = scan_third_party(cfg)

    def _importable(mod):
        cmd = [sys.executable, "-c", "import %s" % mod]
        try:
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, encoding="utf-8", errors="replace",
            )
            out, _e = p.communicate(timeout=30)
            return p.returncode == 0, (out or "").strip().splitlines()[-1:] or [""]
        except Exception as e:
            return False, [str(e)]

    missing = {}
    satisfied = {}
    for mod, users in sorted(found.items()):
        ok, _msg = _importable(mod)
        (satisfied if ok else missing)[mod] = sorted(users)

    if not found:
        return {
            "level": "ok", "title": "第三方依赖",
            "detail": "零依赖：扫描 %d 个脚本，未发现任何非标准库 import（拷走即可用）" % scanned,
        }

    if not missing:
        return {
            "level": "ok", "title": "第三方依赖",
            "detail": "扫描 %d 个脚本，发现外部包 %s —— 本机均已可用" % (
                scanned, "、".join(sorted(satisfied))),
        }

    idx = cfg.get("pip_index_url", "")
    lines = []
    fixes = []
    for mod, users in sorted(missing.items()):
        lines.append("缺少 %s（被 %s 引用）" % (mod, "、".join(users)))
        fixes.append("%s -m pip install %s%s" % (
            _py_cmd_hint(), mod, (" -i " + idx) if idx else ""))
    return {
        "level": "fail", "title": "第三方依赖",
        "detail": "；".join(lines),
        "fix": " / ".join(fixes) + "　（或直接跑：%s scripts/setup_env.py --fix）" % _py_cmd_hint(),
        "missing_modules": sorted(missing),
    }


def check_files(cfg):
    need = cfg.get("required_files", [])
    miss = [x for x in need if not os.path.isfile(os.path.join(ROOT, x))]
    if miss:
        return {
            "level": "fail", "title": "必需文件",
            "detail": "缺 %d / %d：%s" % (len(miss), len(need), "、".join(miss[:8]) + ("…" if len(miss) > 8 else "")),
            "fix": "把缺的文件补回 skill 目录（这些是方法与口径的载体，缺了会静默降级）",
            "missing_files": miss,
        }
    return {"level": "ok", "title": "必需文件", "detail": "%d / %d 齐" % (len(need), len(need))}


def run_script(rel, args, timeout=180, extra_env=None):
    cmd = [sys.executable, os.path.join(ROOT, rel)] + list(args)
    env = None
    if extra_env:
        env = dict(os.environ)
        env.update(extra_env)
    try:
        p = subprocess.Popen(
            cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, encoding="utf-8", errors="replace", env=env,
        )
        out, _e = p.communicate(timeout=timeout)
        return p.returncode, (out or "")
    except subprocess.TimeoutExpired:
        try:
            p.kill()
        except Exception:
            pass
        return -9, "[超时 %ds]" % timeout
    except Exception as e:
        return -1, "[无法启动] %s" % e


def check_entrypoints(cfg):
    eps = cfg.get("entrypoints", [])
    bad = []
    for ep in eps:
        rel = ep["script"]
        if not os.path.isfile(os.path.join(ROOT, rel)):
            bad.append((rel, "文件不存在"))
            continue
        rc, out = run_script(rel, ["--help"], timeout=60)
        if rc != 0:
            bad.append((rel, (out.strip().splitlines() or ["未知错误"])[-1][:120]))
    if bad:
        return {
            "level": "fail", "title": "脚本入口",
            "detail": "；".join("%s（%s）" % (a, b) for a, b in bad),
            "fix": "先修依赖（见上一条），再重跑本自检",
            "bad_entrypoints": [a for a, _b in bad],
        }
    return {"level": "ok", "title": "脚本入口", "detail": "%d / %d 可运行" % (len(eps), len(eps))}


def check_smoke(cfg):
    tests = cfg.get("smoke_tests", [])
    tmp_out = os.path.join(ROOT, "_smoke_tmp.md")
    if os.path.isfile(tmp_out):
        try:
            os.remove(tmp_out)
        except Exception:
            pass
    bad = []
    for t in tests:
        args = [tmp_out if a == "__SMOKE_OUT__" else a for a in t.get("args", [])]
        rc, out = run_script(t["script"], args, timeout=180)
        if rc != 0:
            bad.append((t["script"], "退出码 %s" % rc))
            continue
        miss = [k for k in t.get("expect", []) if k not in out]
        if miss:
            bad.append((t["script"], "输出里找不到：%s" % "、".join(miss)))
            continue
        # 有的脚本把结果写进文件而不打印，这时要看产物
        need_file = t.get("expect_file", [])
        if need_file:
            if not os.path.isfile(tmp_out):
                bad.append((t["script"], "没有生成输出文件"))
                continue
            try:
                with open(tmp_out, "r", encoding="utf-8") as f:
                    body = f.read()
            except Exception as e:
                bad.append((t["script"], "输出文件读不出来：%s" % e))
                continue
            miss_f = [k for k in need_file if k not in body]
            if miss_f:
                bad.append((t["script"], "输出文件里找不到：%s" % "、".join(miss_f)))
    if os.path.isfile(tmp_out):
        try:
            os.remove(tmp_out)
        except Exception:
            pass
    if bad:
        return {
            "level": "fail", "title": "冒烟测试（示例假盘）",
            "detail": "；".join("%s → %s" % (a, b) for a, b in bad),
            "fix": "按上面报的脚本逐个排查；本节全部用**假盘**，不涉及任何真人命盘",
            "bad_smoke": [a for a, _b in bad],
        }
    return {"level": "ok", "title": "冒烟测试（示例假盘）", "detail": "%d / %d 通过" % (len(tests), len(tests))}


def check_writable():
    probe = os.path.join(ROOT, "_write_probe.tmp")
    try:
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return {"level": "ok", "title": "输出可写", "detail": "可在 skill 目录写临时文件"}
    except Exception as e:
        return {
            "level": "warn", "title": "输出可写", "detail": "skill 目录不可写：%s" % e,
            "fix": "改用 --out 指定一个可写路径（如用户目录下），或将 skill 放到可写位置",
        }


def check_absolute_paths(cfg):
    """外传体检：scripts/ 与 config/ 里不应出现本机绝对路径。

    模式要点（否则会大面积误报）：
      · 盘符前不能是字母数字 —— 挡掉 `https://` 的 `s://`
      · 冒号后必须是反斜杠、或**后面不跟斜杠**的正斜杠 —— 挡掉 YAML 里的 `键:\\s*` 与 URL
      · 跳过 setup_env.py 自己（它正文里含这个模式本身）
    """
    PAT = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\{1,2}|/(?![/\\]))")
    hits = []
    for base in (HERE, os.path.join(ROOT, "config")):
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not (fn.endswith(".py") or fn.endswith(".json")):
                continue
            if fn == os.path.basename(__file__):
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    src = f.read()
            except Exception:
                continue
            for m in PAT.finditer(src):
                line_no = src[:m.start()].count("\n") + 1
                hits.append("%s:%d" % (fn, line_no))
    if hits:
        return {
            "level": "warn", "title": "外传体检（绝对路径）",
            "detail": "scripts/config 里出现本机盘符路径：%s" % "、".join(hits[:6]),
            "fix": "改成基于 __file__ 的相对定位（skill 要能拷到别人机器上跑）",
        }
    return {"level": "ok", "title": "外传体检（绝对路径）", "detail": "scripts / config 里无本机盘符路径"}


def _py_cmd_hint():
    """给出本机可照抄的解释器命令。"""
    exe = sys.executable or "python"
    return '"%s"' % exe if " " in exe else exe


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run_all(cfg):
    return [
        check_python(cfg),
        check_third_party(cfg),
        check_files(cfg),
        check_entrypoints(cfg),
        check_smoke(cfg),
        check_writable(),
        check_absolute_paths(cfg),
    ]


MARK = {"ok": "✅", "warn": "⚠️", "fail": "❌"}


def render(results, cfg, quiet=False, elapsed=None):
    fails = [r for r in results if r["level"] == "fail"]
    warns = [r for r in results if r["level"] == "warn"]
    lines = []
    if not quiet:
        lines.append("=" * 64)
        lines.append("  %s skill · 环境自检（setup_env）" % cfg.get("skill", "bazi"))
        lines.append("=" * 64)
        lines.append("解释器   ：%s" % sys.executable)
        lines.append("版本     ：%d.%d.%d" % sys.version_info[:3])
        lines.append("平台     ：%s" % sys.platform)
        lines.append("skill 根 ：%s" % ROOT)
        lines.append("-" * 64)
        for i, r in enumerate(results, 1):
            lines.append("[%d/%d] %-16s %s %s" % (
                i, len(results), r["title"], MARK[r["level"]], r["detail"]))
        lines.append("-" * 64)
        if fails:
            lines.append("❌ 环境未就绪 —— %d 项待修：" % len(fails))
            for i, r in enumerate(fails, 1):
                lines.append("  %d) [%s] %s" % (i, r["title"], r["detail"]))
                if r.get("fix"):
                    lines.append("     修复：%s" % r["fix"])
        else:
            tail = "，另有 %d 项提醒" % len(warns) if warns else ""
            lines.append("✅ 环境就绪：拷走即可用，不需要 pip、不需要联网%s。" % tail)
            lines.append("   后续所有命令用本机解释器：%s" % _py_cmd_hint())
            lines.append("   （Windows 上若没有 python3 命令，就把文档里的 python3 换成 python 或 py -3）")
        if elapsed is not None:
            lines.append("   自检耗时 %.1f 秒" % elapsed)
    else:
        lines.append("环境自检：%s（%d 项通过 / %d 项提醒 / %d 项失败）" % (
            "未就绪" if fails else "就绪",
            len(results) - len(fails) - len(warns), len(warns), len(fails)))
        for r in fails:
            lines.append("  ❌ %s：%s" % (r["title"], r["detail"]))
    return "\n".join(lines)


def try_fix(results, cfg):
    idx = cfg.get("pip_index_url", "")
    fixed = []
    for r in results:
        for mod in r.get("missing_modules", []) or []:
            cmd = [sys.executable, "-m", "pip", "install", mod]
            if idx:
                cmd += ["-i", idx]
            _p("→ 尝试补装 %s …" % mod)
            rc, out = run_script_raw(cmd)
            tail = "\n".join((out or "").strip().splitlines()[-3:])
            _p("  退出码 %s\n%s" % (rc, tail))
            if rc == 0:
                fixed.append(mod)
    return fixed


def run_script_raw(cmd):
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, encoding="utf-8", errors="replace",
        )
        out, _e = p.communicate(timeout=600)
        return p.returncode, out
    except Exception as e:
        return -1, str(e)


def main(argv=None):
    ap = argparse.ArgumentParser(description="bazi skill 环境自检与调配（开局先跑）")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    ap.add_argument("--fix", action="store_true", help="尝试自动补装缺失的第三方包（需联网）")
    ap.add_argument("--quiet", action="store_true", help="只输出结论")
    ap.add_argument("--out", default="", help="把报告写入指定文件")
    A = ap.parse_args(argv)

    import time
    t0 = time.time()

    try:
        cfg = load_config()
    except Exception as e:
        _p("❌ 读不到配置文件 config/env.json：%s" % e)
        _p("   这个文件是环境清单（必需文件 / 入口 / 冒烟测试），缺了自检无法进行。")
        return 1

    results = run_all(cfg)

    if A.fix:
        fixes = [r for r in results if r.get("missing_modules")]
        if fixes:
            try_fix(fixes, cfg)
            results = run_all(cfg)

    elapsed = time.time() - t0
    report = render(results, cfg, quiet=A.quiet, elapsed=elapsed)

    if A.json:
        _p(json.dumps({
            "ok": not any(r["level"] == "fail" for r in results),
            "python": "%d.%d.%d" % sys.version_info[:3],
            "interpreter": sys.executable,
            "root": ROOT,
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        _p(report)

    if A.out:
        try:
            with open(A.out, "w", encoding="utf-8") as f:
                f.write("```\n" + report + "\n```\n")
            _p("\n报告已写入：%s" % A.out)
        except Exception as e:
            _p("⚠️ 报告落盘失败：%s" % e)

    return 1 if any(r["level"] == "fail" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
