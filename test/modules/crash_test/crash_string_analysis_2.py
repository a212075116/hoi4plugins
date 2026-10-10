import re
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
data = open(p, 'rb').read()
print('size = %d' % len(data))
strs = re.findall(rb'[\x20-\x7e]{3,}', data)
keys = ['crashes', 'crash', 'Crash', 'CRASH', 'minidump', 'exception.txt', 'meta.yml', 'crash_reporter', 'CrashReporter']
seen = set()
for s in strs:
    t = s.decode('ascii', 'replace')
    if any(k in t for k in keys):
        if t not in seen and len(t) < 160:
            seen.add(t)
print('=== 命中 %d ===' % len(seen))
for t in sorted(seen)[:90]:
    print('  ' + t)
