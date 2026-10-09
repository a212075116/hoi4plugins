import zipfile, re, io
p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/ABY_500_01_01_01.hoi4'
z = zipfile.ZipFile(p)
print('存档内文件:'); 
for n in z.namelist():
    print('   %-20s %d 字节' % (n, z.getinfo(n).file_size))
txt = z.read('gamestate').decode('utf-8', errors='replace')
print('')
print('gamestate 长度: %d 字符' % len(txt))
print('')
for kw in ('fleet=', 'fleet =', 'task_force', 'taskforce', 'navy', 'ships=', 'ship='):
    c = txt.count(kw)
    print('  出现 %-14r : %d 次' % (kw, c))
print('')
i = txt.find('fleet=')
if i < 0: i = txt.find('fleet =')
if i >= 0:
    print('=== 第一处 fleet 附近 800 字符 ===')
    print(txt[max(0,i-300):i+500])
else:
    print('=== 存档里完全没有 fleet 关键字 ===')