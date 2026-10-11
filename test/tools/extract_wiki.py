# -*- coding: utf-8 -*-
import re, html
p = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\wiki\Data structures - Hearts of Iron 4 Wiki.html'
s = open(p, encoding='utf-8', errors='replace').read()
print('html size', len(s))
s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S|re.I)
s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
s = re.sub(r'</(p|div|li|tr|h[1-6]|pre|dd|dt)>', '\n', s, flags=re.I)
t = re.sub(r'<[^>]+>', '', s)
t = html.unescape(t)
t = re.sub(r'[ \t]+', ' ', t)
t = re.sub(r'\n\s*\n+', '\n', t)
lines = [l.strip() for l in t.split('\n')]
lines = [l for l in lines if l]
print('text lines', len(lines))
idxs = [i for i,l in enumerate(lines) if 'set_variable' in l]
print('set_variable at lines:', idxs[:20])
open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools/wiki_data_structures.txt','w',encoding='utf-8').write('\n'.join(lines))
print('saved txt')
