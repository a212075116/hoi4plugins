import sys, json
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
# CCurrentGameState 主虚表 0x2721158, 看看它的所有槽
r = send({'op':'vtable','ea':'0x2721158','max':40})
print('=== ??_7CCurrentGameState@@6B@ @ 0x2721158 的虚表槽 ===')
for s in (r.get('slots') or []):
    print('  [%2d] +0x%03X  %s  %s' % (s['i'], s['i']*8, s['fn'], s['name']))
print()
# 找 0xDC53B0 在哪个虚表槽
print('=== 搜 sub_140DC53B0 在虚表里的位置 ===')
x = send({'op':'xrefs_to','ea':'0x140DC53B0'})
for rf in (x.get('refs') or []):
    print('  %s  in %s' % (rf['from'], rf['func']))
print()
print('=== 读 0x2721158 + 0x130 处的槽 ===')
b = send({'op':'bytes','ea':hex(0x2721158 + 0x130),'n':8})
print('  bytes:', b.get('hex'))
