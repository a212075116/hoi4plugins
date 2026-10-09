import json, os
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/dlc_load.json'
print('改前: %r' % open(p, encoding='utf-8').read())
with open(p, 'w', encoding='utf-8', newline='') as f:
    f.write('{"enabled_mods":[],"disabled_dlcs":[]}')
print('改后: %r' % open(p, encoding='utf-8').read())