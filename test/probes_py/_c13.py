import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x140241DF0','lines':60})
print('=== sub_140241DF0 (capture_commander handler) 前 60 行 ===')
print(r.get('text') if r.get('ok') else str(r.get('err')))
