import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
f = send({'op':'func','ea':'0x1400036F0'})
print('sub_1400036F0: start=%s size=%s' % (f.get('start'), f.get('size')))
print()
r = send({'op':'decompile','ea':'0x1400036F0','lines':110})
print(r.get('text'))
