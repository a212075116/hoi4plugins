import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
s = send({'op':'strings','needle':'debug_zoom','limit':10})
print('=== strings debug_zoom ===')
print(json.dumps(s, ensure_ascii=False)[:1200])
print()
s2 = send({'op':'strings','needle':'Zooms in the game','limit':10})
print('=== strings Zooms in the game ===')
print(json.dumps(s2, ensure_ascii=False)[:1200])
