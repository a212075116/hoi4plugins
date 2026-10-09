p = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/save games/ABY_500_01_01_01.hoi4'
b = open(p, 'rb').read(16)
print('前 16 字节: %r' % b)
print('前 8 字节 hex: %s' % b[:8].hex())
print('')
import gzip, zlib
for name, fn in (('gzip', lambda d: gzip.decompress(d)), ('zlib', lambda d: zlib.decompress(d))):
    try:
        d = fn(open(p, 'rb').read())
        print('%s 解压成功, %d 字节' % (name, len(d)))
        print('  头部: %r' % d[:120])
        break
    except Exception as e:
        print('%s 失败: %s' % (name, str(e)[:80]))