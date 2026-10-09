import json, io
p = r'C:\\Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/continue_game.json'
raw = open(p, encoding='utf-8').read()
print('改前:', repr(raw))
obj = json.loads(raw)
obj['filename'] = 'VANILLA_PATCHED.hoi4'
obj['title'] = 'VANILLA_PATCHED'
out = json.dumps(obj, ensure_ascii=False, indent='\t')
open(p, 'w', encoding='utf-8', newline='').write(out)
print('改后:', repr(open(p, encoding='utf-8').read()))