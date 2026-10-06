# -*- coding: utf-8 -*-
"""十二流月支 × 命局四支 的地支关系对照（六合/六冲/六害/相刑/半合/三会）"""

def _pair(a, b):
    """构造双向查询表"""
    d = {}
    for x, y in zip(a, b):
        d[x] = y
        d[y] = x
    return d


LH = _pair('子寅卯辰巳午', '丑亥戌酉申未')          # 六合
CH = _pair('子丑寅卯辰巳', '午未申酉戌亥')          # 六冲
HAI = _pair('子丑寅卯申酉', '未午巳辰亥戌')         # 六害
# 三合局：中神 -> 另两支
SANHE = {'申': '子辰', '子': '申辰', '辰': '申子',
         '亥': '卯未', '卯': '亥未', '未': '亥卯',
         '寅': '午戌', '午': '寅戌', '戌': '寅午',
         '巳': '酉丑', '酉': '巳丑', '丑': '巳酉'}
JU_NAME = {'申': '水', '子': '水', '辰': '水',
           '亥': '木', '卯': '木', '未': '木',
           '寅': '火', '午': '火', '戌': '火',
           '巳': '金', '酉': '金', '丑': '金'}
SANHUI = [set('亥子丑'), set('寅卯辰'), set('巳午未'), set('申酉戌')]
XING3 = [set('寅巳申'), set('丑戌未')]
ZIXING = set('辰午酉亥')
MONTHS = '寅卯辰巳午未申酉戌亥子丑'


def rel(m, zs):
    out = []
    for z in zs:
        if CH.get(m) == z:
            out.append(f'{m}{z}冲')
        if LH.get(m) == z:
            out.append(f'{m}{z}六合')
        if HAI.get(m) == z:
            out.append(f'{m}{z}害')
        if m == z and m in ZIXING:
            out.append(f'{m}{m}自刑')
        if {m, z} == {'子', '卯'}:
            out.append('子卯刑')
        if SANHE.get(m) and z in SANHE[m]:
            out.append(f'{m}{z}半合{JU_NAME[m]}')
    for S in XING3:
        if m in S:
            hit = [z for z in zs if z in (S - {m})]
            if hit:
                out.append(f'{m}刑{"".join(hit)}')
    for S in SANHUI:
        if m in S:
            others = set(zs) & (S - {m})
            if len(others) >= 2:
                out.append('三会' + ''.join(sorted(S)))
            elif len(others) == 1:
                out.append(f'{m}+{"".join(sorted(others))}半会')
    # 去重保序
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq or ['—']


if __name__ == '__main__':
    # ⚠️ 示例假盘（非真人）
    for name, zs in [('示例盘一', '子寅午申'),
                     ('示例盘二', '子寅午巳')]:
        print(f'==== {name} ====')
        for m in MONTHS:
            print(f'  {m}月  ' + ' / '.join(rel(m, list(zs))))
        print()
