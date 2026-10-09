import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
def git(*a):
    return subprocess.run(['git','-c','safe.directory='+W]+list(a), cwd=W,
                          capture_output=True, text=True, encoding='utf-8').stdout

files = [l for l in git('ls-tree','-r','--name-only','HEAD').splitlines() if l.startswith('hoi4plugins/')]
print('HEAD 中 hoi4plugins 文件总数: %d' % len(files))
print()
from collections import Counter
c = Counter()
for f in files:
    p = f.split('/')
    c['/'.join(p[:2]) if len(p) > 2 else f] += 1
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print('  %-34s %d' % (k, v))
print()
print('=== ai_docs 全部文档 (HEAD 里) ===')
docs = [f for f in files if '/ai_docs/' in f]
for f in sorted(docs):
    print('  ' + f.replace('hoi4plugins/ai_docs/', ''))
print('  共 %d 篇' % len(docs))
print()
print('=== src 全部源码 ===')
for f in sorted([x for x in files if '/src/' in x]):
    print('  ' + f.replace('hoi4plugins/', ''))
print()
print('=== 大文件是否误入 ===')
bad = [f for f in files if f.endswith(('.i64','.id0','.id1','.id2')) or '/build/' in f or '/.vs/' in f]
print('  误入大文件/缓存: %d 个' % len(bad))
for b in bad[:5]: print('    ' + b)
