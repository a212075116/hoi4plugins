import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
# 确认关键符号的 RVA, 并把 sub_140129CA0 的完整尾部读出来(看它是否把 cap 写对)
r = send({'op':'decompile','ea':'0x140129CA0','lines':70})
t = r.get('text') if r.get('ok') else ''
ls = t.split(chr(10))
print('=== sub_140129CA0 尾部 (看 cap/size 怎么写) ===')
print(chr(10).join(ls[24:70]))
