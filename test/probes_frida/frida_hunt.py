import frida, time, os
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
EXE = W + '/hoi4.exe'
SAVE = os.environ.get('FRIDA_START_SAVE', '')
JS = open(W + '/flirt/loader/_hunt.js', encoding='utf-8').read()
args = [EXE, '-gdpr-compliant']
if SAVE: args += ['-start_save=' + SAVE, '-nolauncher', '-allowoldsave']
else: args += ['-continuelastsave']
print('[启动参数] %s' % ' '.join(args), flush=True)
pid = frida.spawn(args)
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
print('[spawn] pid=%d' % pid, flush=True)
t0 = time.time(); last = None
while time.time() - t0 < 220:
    try: st = sc.exports_sync.status()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'):
        key = (st.get('chars'), st.get('countries'))
        if key != last: print('  chars=%s countries=%s (%.0fs)' % (key[0], key[1], time.time()-t0), flush=True); last = key
        if st.get('countries', 0) and st.get('countries') > 50 and st.get('chars', 0) > 10: break
    time.sleep(1)
print('[等待稳定 25s]', flush=True)
time.sleep(25)
r = sc.exports_sync.hunt()
print('')
print('CGameState*  : %s' % r['gs'])
print('chars(角色数): %s' % r['chars'])
print('符号扫描:')
for k, v in r['needles'].items():
    print('   %-22r 命中 %d   %s' % (k, v['count'], v['addrs'][:5]))
print('')
print('CFleet 虚表扫描: %s' % r['vtscan'])
print('CCharacter 正对照: %s' % r.get('charCheck'))
try: frida.kill(pid)
except Exception: pass