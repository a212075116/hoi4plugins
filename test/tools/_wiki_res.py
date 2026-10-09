import re, html
H = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/wiki/Effect - Hearts of Iron 4 Wiki.html'
t = open(H, encoding='utf-8', errors='replace').read()
t = re.sub(r'<script.*?</script>', ' ', t, flags=re.S|re.I)
t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S|re.I)
t = re.sub(r'</(td|th)>', ' | ', t, flags=re.I)
t = re.sub(r'</(tr|div|p|li|h[1-6])>', chr(10), t, flags=re.I)
t = re.sub(r'<[^>]+>', '', t)
t = html.unescape(t)
lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in t.split(chr(10))]
lines = [l for l in lines if l]
keys = ['set_date', 'game_date', 'change_date', 'set_game_date', 'advance_date', 'current_date', 'days', 'date =']
seen = set()
hit = 0
for i, l in enumerate(lines):
    low = l.lower()
    if any(k in low for k in ['date']) and ('=' in l or 'date' in low[:30]):
        if len(l) > 200: continue
        # 只保留看起来像 effect 名字/说明的
        if re.match(r'^[a-z_]+$', l) or '=' in l[:60] or 'date' in low[:40]:
            rng = range(max(0, i-1), min(len(lines), i+3))
            for j in rng:
                if j in seen: continue
                seen.add(j)
                print('%5d: %s' % (j, lines[j][:180]))
            print('  ---')
            hit += 1
            if hit > 40: break
