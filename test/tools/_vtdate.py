import json
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/sources/1.19.3/vt_index_1.19.3.json'
d = json.loads(open(p, encoding='utf-8', errors='replace').read())
for k in d.keys():
    v = d[k]
    t = type(v).__name__
    if isinstance(v, (list, dict)):
        print('%-16s %-6s len=%d' % (k, t, len(v)))
    else:
        print('%-16s %-6s %s' % (k, t, str(v)[:80]))
print()
# 找看起来像虚表条目的键
for k in d.keys():
    v = d[k]
    if isinstance(v, list) and len(v) > 100:
        print('=== %s 第一项 ===' % k)
        print(json.dumps(v[0], ensure_ascii=False)[:400])
        print('=== 含 Date 的项 ===')
        hits = [x for x in v if 'Date' in json.dumps(x, ensure_ascii=False)]
        print('  共 %d 个' % len(hits))
        for x in hits[:30]:
            print('  %s' % json.dumps(x, ensure_ascii=False)[:220])
