import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
print('=== sub_1400036F0 开头 45 条指令 ===')
d = send({'op':'disasm','ea':'0x1400036F0','count':45,'back':0})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
print()
print('=== add_stability 在 sub_1400036F0 里的引用点上下文 (0x14000DCF4) ===')
d2 = send({'op':'disasm','ea':'0x14000DCF4','count':16,'back':10})
t2 = d2.get('text') or d2.get('lines') or ''
print(t2 if isinstance(t2,str) else chr(10).join(t2))
