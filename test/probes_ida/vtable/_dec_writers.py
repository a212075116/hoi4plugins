import sys, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
from idalib_cli import send
cands = ['0x141261320','0x141264150','0x1412642A0','0x1412643F0','0x141263330']
CAM_FIELDS = ['678h','69Ch','684h','6D0h','6D4h','6F0h','6F4h','6FCh','674h','67Ch','6C8h','6CCh']
for ea in cands:
    f = send({'op':'func','ea':ea})
    r = send({'op':'decompile','ea':ea,'lines':120})
    t = r.get('text') if r.get('ok') else ''
    ls = t.split(chr(10))
    # 统计它碰了摄像机哪些字段
    hit = {}
    for fld in CAM_FIELDS:
        n = sum(1 for l in ls if fld in l)
        if n: hit[fld] = n
    print('=' * 78)
    print('=== %s  %s  size=%s ===' % (ea, f.get('name'), f.get('size')))
    print('    碰到的摄像机字段: %s' % (hit if hit else '(无)'))
    print('=' * 78)
    print(chr(10).join(ls[:min(46, len(ls))]))
    print()
