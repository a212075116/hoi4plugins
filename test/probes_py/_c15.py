import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x1402856A0','lines':80})
t = r.get('text') if r.get('ok') else ''
print('=== sub_1402856A0 (bop_set handler) ===')
print(chr(10).join(t.split(chr(10))[:70]))
