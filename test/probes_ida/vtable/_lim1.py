import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== 服务状态 ===')
try:
    p = send({'op':'ping'})
    print('  ' + str(p))
except Exception as e:
    print('  ping 失败: ' + str(e))
print()
print('=== 找 cam+0x6D0 / +0x6D4 的写者 (指令级搜索) ===')
r = send({'op':'find_off_write','off':0x6D0,'limit':30})
if r.get('error'):
    print('  不支持的 op: ' + str(r))
else:
    print('  命中 %s' % r.get('count'))
    for it in (r.get('items') or [])[:20]:
        print('    %s  %s' % (it.get('ea'), it.get('func')))
