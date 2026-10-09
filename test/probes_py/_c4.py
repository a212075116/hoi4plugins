import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
# debug_zoom 表项的连续存储字段
sites = [
  ('0x1400097ad', 'mov [var_185B8], rax   <- handler'),
  ('0x1400097b4', 'mov [var_185B0], 0'),
  ('0x1400097bf', 'mov [var_185A8], 0'),
  ('0x1400097ca', 'mov [var_185A0], 0'),
]
for ea, label in sites:
    r = send({'op':'bytes','ea':ea,'n':14})
    print('%s  %-32s -> %s' % (ea, label, r.get('hex')))
print()
print('remove_core 的 +0x80 = 1 处:')
r = send({'op':'bytes','ea':'0x14000970a','n':12})
print('  0x14000970a  mov [var_18768], 1   ->', r.get('hex'))
print()
print('remove_core 的 +0x70/+0x78 处:')
for ea in ['0x1400096f4','0x1400096ff']:
    r = send({'op':'bytes','ea':ea,'n':12})
    print('  %s -> %s' % (ea, r.get('hex')))
