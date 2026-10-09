import re, sys
p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"
data = open(p, "rb").read()
print("size", len(data))
# 扫 ASCII 字符串
pat = re.compile(rb"[ -~]{5,80}")
keys = ["loadgame", "load_game", "continuelastsave", "continue_game", "mainmenu", "-load", "startgame", "quickstart", "autosave", "savestate", "playgame", "newgame", "new_game", "skipmenu", "nomenu", "frontend"]
seen = set()
for m in pat.finditer(data):
    s = m.group().decode("ascii", "ignore")
    low = s.lower()
    for k in keys:
        if k in low and s not in seen:
            seen.add(s)
            print("  [%-14s] 0x%X  %s" % (k, m.start(), s))
            break
print("total hits", len(seen))