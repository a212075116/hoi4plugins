# gen_prov_names_mod_only.py -- 只用 mod 自己的数据生成「省份 id -> 名字」完整对照
#
# 数据来源(全部在 mod 内, 不涉及游戏本体 localisation):
#   1) mod/bakaifa/history/states/*.txt  里的 victory_points = { <省份id> <值> }
#   2) mod/bakaifa/localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml
#   3) mod/bakaifa/localisation/english/ba_victory_points_l_english.yml
#
# 关于 mod 的覆盖机制(实测):
#   mod/simp_chinese/victory_points_l_simp_chinese.yml     3 字节(只有 BOM, 内容为空)
#   mod/english/victory_points_l_english.yml               5 字节(内容为空)
#   -> mod 用空文件覆盖了原版的胜利点本地化, 名字全部来自 ba_victory_points_l_*.yml
#
# 本脚本不做任何集合差分, 只输出 id -> 名字的完整对照。
import re, os, glob

MOD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_mod数据_省份id与名字完整对照.txt'

def load_vp(lang):
    m = {}
    f = os.path.join(MOD, 'localisation', lang, 'ba_victory_points_l_%s.yml' % lang)
    if not os.path.exists(f): return m
    for line in open(f, encoding='utf-8-sig', errors='ignore'):
        mm = re.match(r'^\s*VICTORY_POINTS_(\d+)\s*:\s*"(.*)"\s*$', line.strip())
        if mm: m[int(mm.group(1))] = mm.group(2)
    return m

cn = load_vp('simp_chinese')
en = load_vp('english')

# 从 state 文件里收集: state id -> (name, [省份id...], [胜利点省份id...])
states = []
for fp in sorted(glob.glob(os.path.join(MOD, 'history/states/*.txt'))):
    txt = open(fp, encoding='utf-8-sig', errors='ignore').read()
    sid = re.search(r'^\s*id\s*=\s*(\d+)', txt, re.M)
    nm  = re.search(r'^\s*name\s*=\s*"([^"]*)"', txt, re.M)
    provs = []
    mb = re.search(r'provinces\s*=\s*\{([^}]*)\}', txt)
    if mb: provs = [int(x) for x in re.findall(r'\d+', mb.group(1))]
    vps = []
    for blk in re.findall(r'victory_points\s*=\s*\{([^}]*)\}', txt):
        for mm in re.finditer(r'(\d+)\s+(\d+)', blk):
            vps.append((int(mm.group(1)), int(mm.group(2))))
    states.append({'file': os.path.basename(fp),
                   'sid': int(sid.group(1)) if sid else None,
                   'name': nm.group(1) if nm else None,
                   'provs': provs, 'vps': vps})

L = []
def a(s): L.append(str(s))
a('时间戳       : 20261009_015321')
a('测试模块     : mod/bakaifa (不涉及游戏本体 localisation)')
a('数据来源     : mod/bakaifa/history/states/*.txt')
a('               mod/bakaifa/localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml')
a('               mod/bakaifa/localisation/english/ba_victory_points_l_english.yml')
a('测试目的     : 列出 mod 里每个省份 id 对应的名字')
a('完整性问题   : 全量输出, 不抽样, 不过滤')
a('')
a('mod 的本地化覆盖情况(实测字节数):')
a('  localisation/simp_chinese/victory_points_l_simp_chinese.yml      3 字节(仅 BOM, 空)')
a('  localisation/english/victory_points_l_english.yml                5 字节(空)')
a('  localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml %d 字节  %d 条' % (os.path.getsize(os.path.join(MOD,'localisation/simp_chinese/ba_victory_points_l_simp_chinese.yml')), len(cn)))
a('  localisation/english/ba_victory_points_l_english.yml           %d 字节  %d 条' % (os.path.getsize(os.path.join(MOD,'localisation/english/ba_victory_points_l_english.yml')), len(en)))
a('  -> mod 用空文件覆盖原版, 名字全部来自 ba_victory_points_l_*.yml')
a('')
a('state 文件数: %d' % len(states))
allvp = {}
for s in states:
    for pid, val in s['vps']:
        allvp.setdefault(pid, []).append((s['sid'], val))
a('出现了胜利点的省份 id 数: %d' % len(allvp))
a('')
a('=' * 118)
a('省份 id -> 名字   (名字取自 mod 的 ba_victory_points_l_simp_chinese.yml)')
a('=' * 118)
a('%-10s %-24s %-24s %-8s %s' % ('省份id', '中文名', '英文名', '胜利点值', '所属州(id/名)'))
a('-' * 118)
ncn = 0; nen = 0; nnone = 0
for pid in sorted(allvp):
    c = cn.get(pid); e = en.get(pid)
    owners = allvp[pid]
    ost = '; '.join('%s/%s' % (o[0], (next((x['name'] for x in states if x['sid']==o[0]), '?') or '?')) for o in owners)
    pv = ','.join(str(o[1]) for o in owners)
    if c: ncn += 1
    if e: nen += 1
    if not c and not e: nnone += 1
    a('%-10d %-24s %-24s %-8s %s' % (pid, (c if c else '(无)'), (e if e else '(无)'), pv, ost))
a('')
a('统计: 共 %d 个省份有胜利点; 有中文名 %d; 有英文名 %d; 两者都没有 %d' % (len(allvp), ncn, nen, nnone))

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s' % OUT)
print('[行数] %d' % len(L))
print('[省份数] %d  中文名 %d  英文名 %d  都无 %d' % (len(allvp), ncn, nen, nnone))
print('')
print('=== 前 30 条 ===')
print('%-10s %-24s %-24s' % ('省份id', '中文名', '英文名'))
for pid in sorted(allvp)[:30]:
    print('%-10d %-24s %-24s' % (pid, cn.get(pid, '(无)'), en.get(pid, '(无)')))