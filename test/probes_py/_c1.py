import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
print('=== debug_zoom 字符串位置 ===')
r = send({'op':'names','pat':'aDebugZoom'})
print(json.dumps(r, ensure_ascii=False)[:800])
print()
x = send({'op':'xrefs_to','ea':'0x142A2C5A0'})
print('试探性 xrefs:', json.dumps(x, ensure_ascii=False)[:400])
print()
# 用 strings 找 debug_zoom 的实际地址
s = send({'op':'strings','pat':'debug_zoom','limit':10})
print('=== strings debug_zoom ===')
print(json.dumps(s, ensure_ascii=False)[:1500])
