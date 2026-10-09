import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
f = send({'op':'func','ea':'0x140299AD0'})
print('=== sub_140299AD0 %s size=%s ===' % (f.get('name'), f.get('size')))
r = send({'op':'decompile','ea':'0x140299AD0','lines':200})
print(r.get('text') if r.get('ok') else str(r.get('err')))
