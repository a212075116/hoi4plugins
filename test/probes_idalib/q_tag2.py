import json
d = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vt_list.json', encoding='utf-8'))
vts = d['vt']
print('=== 包含 CountryTag 的虚表 ===')
seen = set()
for v in vts:
    s = (str(v.get('cls','')) + ' ' + str(v.get('sym','')))
    if 'CountryTag' in s:
        c = v.get('cls')
        if c in seen: continue
        seen.add(c)
        print('  rva=%#x  n=%-3s  cls=%s' % (v.get('rva',0), v.get('n'), c))
print()
print('=== 包含 PdxHybridInlineBufferAllocator 的 (看看还有哪些类用了这个容器) ===')
seen2 = set()
cnt = 0
for v in vts:
    c = str(v.get('cls',''))
    if 'PdxHybridInlineBufferAllocator' in c:
        if c in seen2: continue
        seen2.add(c)
        cnt += 1
        if cnt <= 25: print('  ' + c)
print('  共 %d 种' % cnt)