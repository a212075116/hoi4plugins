import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
IMG = 0x140000000
names = ['add_stability','add_manpower','add_war_support','add_political_power','set_global_flag','add_country_leader_trait']
for nm in names:
    r = send({'op':'strings','needle':nm,'limit':6})
    items = r.get('items') or []
    print('=== "%s"  命中 %s 条 ===' % (nm, r.get('count')))
    for it in items[:4]:
        ea = int(it['ea'], 16)
        x = send({'op':'xrefs_to','ea':hex(ea)})
        print('   %s  "%s"   引用 %s 处' % (it['ea'], it.get('s','')[:44], x.get('count')))
        for rf in (x.get('refs') or [])[:4]:
            print('        %s  in %s' % (rf['from'], rf['func']))
    print()
