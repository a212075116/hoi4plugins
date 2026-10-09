import struct
p = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
d = open(p, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe+6)[0]
optsz = struct.unpack_from('<H', d, pe+20)[0]
secs = []
off = pe + 24 + optsz
for i in range(nsec):
    b = d[off+i*40: off+i*40+40]
    name = b[:8].rstrip(b'\x00').decode('latin1')
    vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
    secs.append((name, vaddr, vsize, raw, rsize))
def rva2off(rva):
    for name, vaddr, vsize, raw, rsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return raw + (rva - vaddr)
    return None
print('=== 被复用的地址到底是什么函数 ===')
for abs_ea, nm in [(0x14012A2C0, '_guard_check_icall_nop'),
                   (0x140120540, 'UserMathErrorFunction'),
                   (0x14253C3B8, '_purecall'),
                   (0x140BEF1F0, 'vfunc_7 of CUnit_1')]:
    rva = abs_ea - 0x140000000
    o = rva2off(rva)
    if o is None:
        print('0x%X  %s  -> 不在文件映射区' % (abs_ea, nm))
        continue
    by = d[o:o+24]
    print('0x%-12X %-26s 前24字节: %s' % (abs_ea, nm, by.hex(' ')))
print()
print('=== 检查 CUnit 主虚表里有几个不同的地址 ===')
RVA = 0x29530D8
seen = []
for k in range(58):
    o = rva2off(RVA + k*8)
    v = struct.unpack_from('<Q', d, o)[0]
    seen.append(v)
uniq = sorted(set(seen))
print('58 个槽位中不同地址数 = %d' % len(uniq))
import collections
c = collections.Counter(seen)
print('出现次数最多的地址:')
for v, n in c.most_common(8):
    print('   0x%-12X 出现 %d 次' % (v, n))
print()
print('=== 对比 .text 段大小与这些地址 ===')
print('  .text RVA 范围: 0x1000 .. 0x%X' % (0x1000 + 0x27050D8))
