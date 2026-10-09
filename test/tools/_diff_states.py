import os, re, difflib
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
files = {}
for fn in os.listdir(SD):
    m = re.match(r'^(\d+)-', fn)
    if m: files[int(m.group(1))] = fn
def load(i):
    return open(os.path.join(SD, files[i]), encoding='utf-8-sig', errors='replace').read().splitlines()
def show(i, tag):
    print('=== id=%d (%s) ===' % (i, tag))
    for l in load(i):
        print('  ' + l)
    print()
show(2, '变0')
show(7, '保持')
print('=== 两者的差异 ===')
a = load(2); b = load(7)
for l in difflib.unified_diff(a, b, lineterm='', n=1):
    print('  ' + l)
