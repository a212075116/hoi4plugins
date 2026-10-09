import json
p = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\reports\live_objects4.json"
d = json.load(open(p, encoding="utf-8"))
print("%-14s %-12s %7s %7s %7s %7s  %s" % ("cls","rva","slots","calls","match","mismatch","firstThis"))
for x in d:
    print("%-14s 0x%-10X %7d %7d %7d %7d  %s" % (x["cls"], x["rva"], x["slots"], x["calls"], x["match"], x["mismatch"], x["firstThis"]))