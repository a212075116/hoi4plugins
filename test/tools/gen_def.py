# -*- coding: utf-8 -*-
# 生成 .def 转发文件。用法: gen_def.py <源DLL> <输出def> <LIBRARY名> <转发目标模块名>
#
# 要点: 全部导出都要转发, 包括 C++ 修饰名(?...)。
# 名字里的 @ 在 .def 中与序号语法歧义, 但 lib.exe 能正确接受这种写法;
# 且 link.exe 那条「跳过含 @ 的名字」的规则反而让我们免于 LNK2001。
import struct, sys


def exports(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    optsz = struct.unpack_from('<H', d, pe + 20)[0]
    magic = struct.unpack_from('<H', d, pe + 24)[0]
    ddoff = pe + 24 + (112 if magic == 0x20B else 96)
    secs = []
    off = pe + 24 + optsz
    for i in range(nsec):
        b = d[off + i * 40: off + i * 40 + 40]
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', b, 8)
        secs.append((vaddr, vsize, raw, rsize))

    def r2o(rva):
        for vaddr, vsize, raw, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raw + (rva - vaddr)
        return None

    erva = struct.unpack_from('<I', d, ddoff)[0]
    if not erva:
        return []
    o = r2o(erva)
    nnames = struct.unpack_from('<I', d, o + 0x18)[0]
    npo = r2o(struct.unpack_from('<I', d, o + 0x20)[0])
    res = []
    for i in range(nnames):
        nr = struct.unpack_from('<I', d, npo + i * 4)[0]
        no = r2o(nr)
        res.append(d[no:no + 512].split(b'\x00')[0].decode('latin1'))
    return res


def main():
    src, out, libname, tgt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    ex = exports(src)
    lines = ['LIBRARY %s' % libname, 'EXPORTS']
    seen = set()
    n = 0
    for e in ex:
        if e in seen:
            continue
        seen.add(e)
        lines.append('    %s=%s.%s' % (e, tgt, e))
        n += 1
    open(out, 'w', encoding='ascii').write('\n'.join(lines) + '\n')
    print('  exports=%d  forwarded=%d' % (len(ex), n))
    return len(ex), n


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--count':
        print(len(exports(sys.argv[1])))
    else:
        main()