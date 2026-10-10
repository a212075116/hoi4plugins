import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
needles = ['CTokenTable','CTokenDef','TokenTable','CToken','CLexer','CStringTable','_Token','EffectEntries','CTokenHelper']
for needle in needles:
    n = send({'op':'names','needle':needle,'limit':8})
    print('  "%s": %s 个' % (needle, n.get('count')))
    for it in (n.get('items') or [])[:5]:
        print('      %s  %s' % (it['ea'], it['name']))
