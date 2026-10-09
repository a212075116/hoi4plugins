import re
p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"
data = open(p, "rb").read()
pat = re.compile(rb"[ -~]{3,120}")
strs = [(m.start(), m.group().decode("ascii","ignore")) for m in pat.finditer(data)]
print("total strings", len(strs))

# 找参数解析附近的字符串：定位含 "quickstart" 的位置，看周围
idx = None
for i,(o,s) in enumerate(strs):
    if s == "quickstart": idx = i; break
if idx is not None:
    print("=== quickstart 周围 (index %d) ===" % idx)
    for j in range(max(0, idx-30), min(len(strs), idx+30)):
        o, s = strs[j]
        mark = "  <<<" if j == idx else ""
        print("   0x%X  %s%s" % (o, s[:100], mark))

print()
print("=== 候选参数名（全部小写单词，5~22 字符）===")
kw = ["tag","start","observer","country","scenario","bookmark","menu","skip","auto","load","save","continue","quick","new"]
seen=set()
for o,s in strs:
    if not (3 <= len(s) <= 22): continue
    if not re.fullmatch(r"[a-z_][a-z0-9_]{2,21}", s): continue
    if not any(k in s for k in kw): continue
    if s in seen: continue
    seen.add(s)
print("  " + ", ".join(sorted(seen)))