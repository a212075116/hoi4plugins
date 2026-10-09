import re, os
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crash_reporter/binaries/CrashReporter.exe'
data = open(p, 'rb').read()
print('size = %d' % len(data))
# 提取 ASCII 字符串
strs = re.findall(rb'[\x20-\x7e]{5,}', data)
pats = ['crash', 'Crash', 'dump', 'Dump', 'folder', 'Folder', 'dir', 'Dir', 'path', 'Path', 'tmp', 'Tmp', 'User', 'Document', 'arg', 'Arg', '--', '-']
seen = set()
hits = []
for s in strs:
    t = s.decode('ascii', 'replace')
    if any(k in t for k in ['crash-dir','crashdir','dump-dir','dumpdir','output','Output','directory','Directory','folder','Folder','/crash','--crash','-crash','--dump','-dump']):
        if t not in seen:
            seen.add(t)
            hits.append(t)
print('=== 路径/参数相关字符串 (%d) ===' % len(hits))
for h in hits[:70]:
    print('  ' + h[:150])
