import struct, os
ROOT = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'

def dirs_of(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    nsec = struct.unpack_from('<H', d, pe+6)[0]
    optsz = struct.unpack_from('<H', d, pe+20)[0]
    magic = struct.unpack_from('<H', d, pe+24)[0]
    ddoff = pe + 24 + (112 if magic == 0x20B else 96)
    secs = []
    off = pe + 24 + optsz
    for i in range(nsec):
        b = d[off+i*40: off+i*40+40]
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
        secs.append((vaddr, vsize, raw, rsize))
    def r2o(rva):
        for vaddr, vsize, raw, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raw + (rva - vaddr)
        return None
    out = {}
    for idx, nm in [(0,'export'), (1,'import'), (2,'resource'), (14,'manifest')]:
        rva, size = struct.unpack_from('<II', d, ddoff + idx*8)
        out[nm] = (rva, size)
    # TLS directory is idx 9
    rva9, size9 = struct.unpack_from('<II', d, ddoff + 9*8)
    out['tls'] = (rva9, size9)
    return out, d, r2o, secs

print('=== hoi4.exe 的 manifest（DLL 重定向声明就在这里）===')
info, d, r2o, secs = dirs_of(os.path.join(ROOT, 'hoi4.exe'))
rva, size = info['manifest']
print('manifest 目录项: RVA=0x%X size=%d' % (rva, size))
if rva:
    o = r2o(rva)
    if o:
        xml = d[o:o+size].decode('utf-8', 'replace')
        print('--- manifest 内容 ---')
        print(xml[:2000])
else:
    print('>>> hoi4.exe 没有嵌入 manifest' )
print()
print('=== TLS 目录（可能有 TLS 回调，是另一种注入点）===')
rva, size = info['tls']
print('TLS 目录: RVA=0x%X size=%d' % (rva, size))
print()
print('=== 游戏根目录下的 .local / .manifest 文件 ===')
found = False
for f in os.listdir(ROOT):
    low = f.lower()
    if low.endswith('.local') or low.endswith('.manifest'):
        print('   %s  (%d bytes)' % (f, os.path.getsize(os.path.join(ROOT, f))))
        found = True
if not found:
    print('   无（DLL 重定向未启用）')
print()
print('=== 检查 hoi4.exe.manifest 是否为外部文件 ===')
p = os.path.join(ROOT, 'hoi4.exe.manifest')
print('   hoi4.exe.manifest 存在 = %s' % os.path.exists(p))
print()
print('=== AppInit_DLLs 注册表（系统级增量加载，非 mod 可用）===')
import winreg
try:
    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
        r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows')
    for v in ['AppInit_DLLs', 'LoadAppInit_DLLs', 'RequireSignedAppInit_DLLs']:
        try:
            val, _ = winreg.QueryValueEx(k, v)
            print('   %-26s = %r' % (v, val))
        except FileNotFoundError:
            print('   %-26s = (不存在)' % v)
except Exception as e:
    print('   读取失败', e)
