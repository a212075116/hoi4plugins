import sys, os
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('ping:', send({'op':'ping'}))
r = send({'op':'names','needle':'??_7','limit':200000})
print('names ??_7 count =', r.get('count'))
items = r.get('items') or []
print('前 3 个:')
for it in items[:3]: print('  ', it['ea'], it['name'])
print('是否被 limit 截断:', 'count 就是总数' if r.get('count') else '?')
