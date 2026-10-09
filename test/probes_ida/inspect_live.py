import json, sys
p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\reports\live_objects4.json"
d = json.load(open(p, encoding="utf-8"))
print("type:", type(d).__name__)
if isinstance(d, dict):
    print("keys:", list(d.keys())[:20])
    for k in list(d.keys())[:6]:
        v = d[k]
        s = json.dumps(v, ensure_ascii=False)
        print("  ", k, "->", type(v).__name__, s[:300])
elif isinstance(d, list):
    print("len:", len(d))
    for x in d[:6]:
        print("  ", json.dumps(x, ensure_ascii=False)[:300])