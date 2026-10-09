import re, html
H = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/wiki/Effect - Hearts of Iron 4 Wiki.html'
t = open(H, encoding='utf-8', errors='replace').read()
# 去 script/style
t = re.sub(r'<script.*?</script>', ' ', t, flags=re.S|re.I)
t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S|re.I)
# 表格/单元格转为分隔, 行转文本
t = re.sub(r'</(td|th)>', ' | ', t, flags=re.I)
t = re.sub(r'</(tr|div|p|li|h[1-6])>', chr(10), t, flags=re.I)
t = re.sub(r'<[^>]+>', '', t)
t = html.unescape(t)
lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in t.split(chr(10))]
lines = [l for l in lines if l]
keys = ['cancel_resistance','set_resistance','add_resistance','set_compliance','add_compliance','start_resistance']
seen = set()
out = []
for i, l in enumerate(lines):
    if any(k in l for k in keys):
        for j in range(max(0,i-3), min(len(lines), i+7)):
            if j in seen: continue
            seen.add(j)
            out.append('%5d: %s' % (j, lines[j][:300]))
        out.append('  ---')
print(chr(10).join(out[:180]))
