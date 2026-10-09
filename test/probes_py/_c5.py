import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x14027BC60','remove_core 的处理函数'), ('0x140250340','debug_zoom 的处理函数')]:
    f = send({'op':'func','ea':ea})
    print('=' * 88)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 88)
    r = send({'op':'decompile','ea':ea,'lines':70})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
print('=== 谁调用这些处理函数? (查 remove_core 处理函数的引用) ===')
x = send({'op':'xrefs_to','ea':'0x14027BC60'})
print('引用数 =', x.get('count'))
for rf in (x.get('refs') or [])[:10]:
    print('   %s  in %s' % (rf['from'], rf['func']))
print()
print('=== 查一个更简单的命令: 处理函数只有 1 个参数的 ===')
s = send({'op':'strings','needle':'Toggles the camera clamping','limit':5})
print(json.dumps(s, ensure_ascii=False)[:400])
