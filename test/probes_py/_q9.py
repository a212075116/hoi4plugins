import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
for ea, label in [('0x14022A730','批量注册 sub_14022A730'), ('0x1402297E0','表项构造 sub_1402297E0'), ('0x14011E130','CString 构造 sub_14011E130')]:
    f = send({'op':'func','ea':ea})
    print('=' * 88)
    print('=== %s  %s  size=%s ===' % (label, f.get('name'), f.get('size')))
    print('=' * 88)
    r = send({'op':'decompile','ea':ea,'lines':110})
    print(r.get('text') if r.get('ok') else ('[失败] ' + str(r.get('err'))))
    print()
print('=== qword_14332F4F8 的引用 ===')
x = send({'op':'xrefs_to','ea':'0x14332F4F8'})
print('引用数 =', x.get('count'))
for rf in (x.get('refs') or [])[:20]:
    print('   %s  in %s (size=%s)' % (rf['from'], rf['func'], rf['func_size']))
