import json, io, sys
sys.stdout.reconfigure = None

p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\reports\class_layouts_full.json"
d = json.load(open(p, encoding="utf-8"))
print("top-level type:", type(d).__name__)
if isinstance(d, dict):
    ks = list(d.keys())
    print("keys:", len(ks))
    print("first 12:", ks[:12])
    k0 = ks[0]
    print("sample key:", k0)
    v = d[k0]
    print("value type:", type(v).__name__)
    print("value sample:", json.dumps(v, ensure_ascii=False)[:900])
elif isinstance(d, list):
    print("len:", len(d))
    print("first:", json.dumps(d[0], ensure_ascii=False)[:900])