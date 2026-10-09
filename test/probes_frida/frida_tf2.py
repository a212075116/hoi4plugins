import frida, time, json, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = W + '/reports/20261009_015321_原版_CHI_CTaskForce_指针全解.txt'
JS = open(W + '/flirt/loader/_tf2.js', encoding='utf-8').read()
try: os.remove(LOG)
except Exception: pass
args = [W + '/hoi4.exe', '-gdpr-compliant', '-start_tag=CHI', '-nolauncher']
print('[启动] %s' % ' '.join(args), flush=True)
pid = frida.spawn(args)
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
t0 = time.time()
while time.time() - t0 < 240:
    try:
        if 'Launching SINGLEPLAYER-game' in open(LOG, encoding='utf-8', errors='ignore').read():
            print('[进入游戏] %.0fs' % (time.time()-t0), flush=True); break
    except Exception: pass
    time.sleep(1)
last = None; stable = 0
while time.time() - t0 < 320:
    try: st = sc.exports_sync.st()
    except Exception as e: st = {'ok': False, 'err': str(e)}
    key = json.dumps(st, ensure_ascii=False, sort_keys=True)
    if key != last: print('[状态 %.0fs] %s' % (time.time()-t0, key), flush=True); last = key; stable = 0
    else: stable += 1
    if (st.get('chi') or {}).get('fleets') and stable >= 4: print('[稳定]', flush=True); break
    time.sleep(5)
d = sc.exports_sync.probeTF()
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('启动参数   : %s' % ' '.join(args))
A('测试目的   : 列出 CTaskForce 每个 8 字节偏移的指针, 找出指向对象数组(含已知虚表)的偏移')
A('完整性     : 全量输出, 不抽样, 不过滤')
A('')
for fr in d.get('fleets', []):
    A('舰队 %s  task_force 数组=%s count=%s' % (fr['fleet'], fr['tfData'], fr['tfCount']))
    for tf in fr['tfs']:
        A('  特遣舰队 %s 虚表=%s' % (tf['ptr'], tf['vt']))
        A('    完整 0x210 字节:')
        h = tf['hex'] or ''
        for row in range(0, len(h), 32):
            A('      +0x%03x  %s' % (row // 2, ' '.join(h[row+i:row+i+2] for i in range(0, min(32, len(h)-row), 2))))
        A('    >>> 指向对象数组(前 64 个 qword 里含已知虚表)的偏移:')
        for hl in tf['hitLists']:
            A('        off=+0x%-4x data=%s' % (hl['off'], hl['data']))
            for hh in hl['hits']:
                A('             [%2d] %s  %s' % (hh['i'], hh['ptr'], hh['vt']))
        A('    其他指针/常量:')
        for pl in tf['plain']:
            if pl['kind'] == 'vtable': A('        off=+0x%-4x = vtable %s' % (pl['off'], pl['name']))
            elif pl['kind'] == 'const': A('        off=+0x%-4x = %s' % (pl['off'], pl['val']))
            else: A('        off=+0x%-4x heap %s head=%s' % (pl['off'], pl['val'], pl['head']))
        A('')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for fr in d.get('fleets', []):
    for tf in fr['tfs']:
        print('特遣舰队 %s 虚表=%s' % (tf['ptr'], tf['vt']))
        for hl in tf['hitLists']:
            print('  off=+0x%-4x data=%s 命中: %s' % (hl['off'], hl['data'], [(h['i'], h['vt']) for h in hl['hits'][:8]]))
try: frida.kill(pid)
except Exception: pass
