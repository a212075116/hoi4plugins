# -*- coding: utf-8 -*-
import sys, os, json, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_CHI_CArmy_与OOB全量对照.txt'
TS = '20261009_015321'

def blocks(text, kw):
    out = []
    for m in re.finditer(r'\b' + kw + r'\s*=\s*\{', text):
        i = m.end() - 1; depth = 0
        for j in range(i, len(text)):
            if text[j] == '{': depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0: out.append(text[i+1:j]); break
    return out

def parse_oob(path):
    t = open(path, encoding='utf-8').read()
    body = (blocks(t, 'units') or [t])[0]
    rows = []
    for b in blocks(body, 'division'):
        loc = re.search(r'\blocation\s*=\s*(\d+)', b)
        tpl = re.search(r'\bdivision_template\s*=\s*"([^"]*)"', b)
        nm = re.search(r'\bname\s*=\s*"([^"]*)"', b)
        rows.append({'tmpl': tpl.group(1) if tpl else None, 'loc': int(loc.group(1)) if loc else None, 'name': nm.group(1) if nm else None})
    return rows

oob = parse_oob(W + '/history/units/CHI_1936_sea.txt')
pid, session, sc, fresh = connect(W + '/flirt/loader/_army_full.js', tag='armyfull')
wait_stable(sc, tag='armyfull')
d = sc.exports_sync.full()
mem = d['armies']

L = []
def A(s): L.append(str(s))
A('时间戳     : %s' % TS)
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('涉及类     : CGameState -> CCountry(+0x290,+0x29C) -> CArmy (继承 CUnit)')
A('涉及函数   : CArmy::ctor sub_140C6D470 ; CUnit::ctor sub_140BF8B50 ; 容器初始化 sub_14011DF40')
A('测试目的   : 内存里 CHI 的 CArmy 全量(85 个) 与 OOB 文件 history/units/CHI_1936_sea.txt 全量对照')
A('为什么是这个 OOB: history/countries/CHI - China.txt 里 has_dlc "No Compromise, No Surrender" 时 set_oob = "CHI_1936_sea", 否则 CHI_1936')
A('关联字段   : CArmy+0x00 虚表 / +0x1C 序号 / +0x28 驻地 province / +0x3B8->+0x20 模板名 / +0x340->+0x60 单位名 / 含 infantry 字样字段 兵种')
A('完整性     : 全量输出, 不抽样')
A('')
A('OOB 文件 %s : %d 个 division' % ('CHI_1936_sea.txt', len(oob)))
A('OOB 模板分布: %s' % dict(Counter(r['tmpl'] for r in oob)))
A('OOB 显式命名: %d 个' % sum(1 for r in oob if r['name']))
A('')
A('内存 CHI CArmy : %d 个' % d['count'])
A('')
A('%-4s %-6s %-6s %-20s %-14s %-18s %-16s' % ('#', 'id1C', 'loc', 'CArmy*', 'vtable', '模板名', '单位名'))
for a in mem:
    A('%-4d %-6s %-6s %-20s %-14s %-18r %-16r' % (a['i'], a['id1C'], a['loc28'], a['ptr'], a['vt'], a['tmpl'], a['unit']))
A('')
A('=== 逐条对照 (按顺序) ===')
A('%-4s %-8s %-20s %-20s %-6s %-6s %s' % ('#', '结果', '内存模板', 'OOB模板', '内存loc', 'OOB loc', '单位名/备注'))
hit_tpl = hit_loc = hit_both = 0
n = max(len(mem), len(oob))
for i in range(n):
    m = mem[i] if i < len(mem) else None
    o = oob[i] if i < len(oob) else None
    mt = m['tmpl'] if m else None
    ot = o['tmpl'] if o else None
    ml = m['loc28'] if m else None
    ol = o['loc'] if o else None
    ok_t = (mt == ot)
    ok_l = (ml == ol)
    hit_tpl += 1 if ok_t else 0
    hit_loc += 1 if ok_l else 0
    hit_both += 1 if (ok_t and ok_l) else 0
    A('%-4d %-8s %-20r %-20r %-6s %-6s %s' % (i, ('OK' if (ok_t and ok_l) else ('模板同' if ok_t else ('驻地同' if ok_l else 'X'))), mt, ot, ml, ol, (m['unit'] if m else '')))
A('')
A('模板名一致 : %d / %d' % (hit_tpl, n))
A('驻地一致   : %d / %d' % (hit_loc, n))
A('两者都一致 : %d / %d' % (hit_both, n))
A('')
A('=== 内存侧模板分布 ===')
A('%s' % dict(Counter((m['tmpl'] or '?') for m in mem)))
A('=== 内存侧兵种分布 ===')
A('%s' % dict(Counter((m['kind'] or '?') for m in mem)))
A('')
A('=== 内存侧单位名全量(按 CArmy 序号) ===')
for a in mem: A('   %3d  %-24r  loc=%-6s tmpl=%r' % (a['i'], a['unit'], a['loc28'], a['tmpl']))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
print('OOB=%d  内存=%d' % (len(oob), d['count']))
print('模板名一致 %d/%d  驻地一致 %d/%d  两者都一致 %d/%d' % (hit_tpl, n, hit_loc, n, hit_both, n))
print('内存模板分布:', dict(Counter((m['tmpl'] or '?') for m in mem)))
print('OOB  模板分布:', dict(Counter((r['tmpl'] or '?') for r in oob)))
for i in range(6):
    m = mem[i]; o = oob[i]
    print('  [%d] mem(tmpl=%r loc=%s) oob(tmpl=%r loc=%s) unit=%r' % (i, m['tmpl'], m['loc28'], o['tmpl'], o['loc'], m['unit']))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
