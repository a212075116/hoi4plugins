import json
p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\reports\class_layouts_full.json"
d = json.load(open(p, encoding="utf-8"))

target = "CGameState"
hits = []
for e in d:
    for pat in e.get("pat", []):
        vt = pat.get("vt", "")
        if target in vt:
            hits.append((e["fn"], e["name"], vt, pat.get("reg"), pat.get("off"), pat.get("store")))
            break

print("CGameState vftable 写入函数数 =", len(hits))
seen = set()
for fn, name, vt, reg, off, store in hits:
    if fn in seen: continue
    seen.add(fn)
    print("  fn=0x%X (%s)  vt=%s  %s+0x%X  store@0x%X" % (fn, name, vt, reg, off, store))

# 顺带看看哪些类被写入次数最多
print()
from collections import Counter
c = Counter()
for e in d:
    for pat in e.get("pat", []):
        vt = pat.get("vt", "")
        if "@@6B@" in vt and vt.startswith("??_7"):
            nm = vt[4:].split("@@")[0]
            c[nm] += 1
print("被写入最多的类 top10:")
for nm, n in c.most_common(10):
    print("  %-40s %d" % (nm, n))