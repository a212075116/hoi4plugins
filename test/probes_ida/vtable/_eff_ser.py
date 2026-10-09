import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
r = send({'op':'strings','needle':'EFFECT_ADD_STABILITY','limit':10})
print('=== "EFFECT_ADD_STABILITY" 命中 %s ===' % r.get('count'))
for it in (r.get('items') or []):
    ea = int(it['ea'], 16)
    x = send({'op':'xrefs_to','ea':hex(ea)})
    print('   %s "%s"  引用 %s 处' % (it['ea'], it.get('s','')[:50], x.get('count')))
    for rf in (x.get('refs') or [])[:5]:
        print('        %s  in %s' % (rf['from'], rf['func']))
print()
print('=== 找 CEffectList / CEffectInstance 之类的类 ===')
for needle in ['CEffectList','CEffectInstance','CEffectContainer','CValueEffect@@6B@']:
    n = send({'op':'names','needle':needle,'limit':6})
    print('  "%s": %s 个' % (needle, n.get('count')))
    for it in (n.get('items') or [])[:4]:
        print('      %s  %s' % (it['ea'], it['name']))
