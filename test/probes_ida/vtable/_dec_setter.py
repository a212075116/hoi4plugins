import sys
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
from idalib_cli import send
print('=' * 78)
print('=== sub_1412643F0 完整 (收 a1 + float a2) ===')
print('=' * 78)
r = send({'op':'decompile','ea':'0x1412643F0','lines':80})
print(r.get('text'))
print()
print('=' * 78)
print('=== sub_141264150 / 2A0 / 3F0 的调用者 ===')
print('=' * 78)
for ea, nm in [('0x141264150','sub_141264150'),('0x1412642A0','sub_1412642A0'),('0x1412643F0','sub_1412643F0')]:
    x = send({'op':'xrefs_to','ea':ea})
    print('%s  被 %s 处引用:' % (nm, x.get('count')))
    for rf in (x.get('refs') or [])[:10]:
        print('    %s  in %s' % (rf['from'], rf['func']))
    print()
print('=' * 78)
print('=== 这三个函数是否在某个虚表里 (用索引表查) ===')
print('=' * 78)
import json, io
d = json.load(io.open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/sources/1.19.3/vt_index_1.19.3.json', encoding='utf-8'))
targets = {0x1264150:'sub_141264150', 0x12642A0:'sub_1412642A0', 0x12643F0:'sub_1412643F0', 0x1261320:'sub_141261320'}
for v in d['vt']:
    for i, s in enumerate(v['slots']):
        if s in targets:
            print('  %-16s 出现在 %-40s 槽[%d] = +0x%X' % (targets[s], (v['cls'] or v['sym'])[:40], i, i*8))
