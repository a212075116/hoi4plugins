# -*- coding: utf-8 -*-
def split_binary(vint):
    u = vint & 0xFFFFFFFFFFFFFFFF
    lo_u = u & 0xFFFFFFFF
    hi_u = (u >> 32) & 0xFFFFFFFF
    lo = lo_u - (1 << 32) if lo_u >= (1 << 31) else lo_u
    hi = hi_u - (1 << 32) if hi_u >= (1 << 31) else hi_u
    return lo, hi

def split_decimal9(vint):
    return vint % (10**9), vint // (10**9)

cases = [
    ('92233720368547', 92233720368547),
    ('92233720368546', 92233720368546),
    ('4294967295', 4294967295),
    ('2147483647', 2147483647),
    ('-92233720368548', -92233720368548),
]
print('%-18s %14s %14s | %14s %14s' % ('V_int', 'lo(binary)', 'hi(binary)', 'lo(dec9)', 'hi(dec9)'))
for name, v in cases:
    lo, hi = split_binary(v)
    d_lo, d_hi = split_decimal9(v)
    print('%-18s %14d %14d | %14d %14d' % (name, lo, hi, d_lo, d_hi))
print()
print('int32 上限 =', 2**31 - 1)
print('9 位十进制上限 =', 10**9 - 1)
print('9 位十进制 2 分量可覆盖 =', 10**18 - 1, ' int64 需要 =', 2**63 - 1)
print('二进制 2x32 位可覆盖 =', 2**63 - 1)
