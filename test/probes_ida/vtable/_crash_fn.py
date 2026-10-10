import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=== sub_1424B5EF0 完整反编译 ===')
r = send({'op':'decompile','ea':'0x1424B5EF0','lines':200})
print(r.get('text'))
