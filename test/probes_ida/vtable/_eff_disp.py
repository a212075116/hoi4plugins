import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
f = send({'op':'func','ea':'0x1400831C0'})
print('sub_1400831C0: start=%s size=%s' % (f.get('start'), f.get('size')))
print()
print('=== add_stability 的引用点 0x140097EC0 上下文 ===')
d = send({'op':'disasm','ea':'0x140097EC0','count':20,'back':14})
t = d.get('text') or d.get('lines') or ''
print(t if isinstance(t,str) else chr(10).join(t))
print()
print('=== sub_1400831C0 开头 30 条 ===')
d2 = send({'op':'disasm','ea':'0x1400831C0','count':30,'back':0})
t2 = d2.get('text') or d2.get('lines') or ''
print(t2 if isinstance(t2,str) else chr(10).join(t2))
