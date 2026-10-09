# -*- coding: utf-8 -*-
# 校验编译产物的导出集合是否覆盖原版导出集合。
# 用法: check_exports.py <我们的DLL> <原版DLL>
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_def import exports

our = exports(sys.argv[1])
ref = exports(sys.argv[2])
so, sr = set(our), set(ref)
missing = sr - so
extra = so - sr
print('  ours=%d  ref=%d' % (len(so), len(sr)))
print('  missing=%d  extra=%d' % (len(missing), len(extra)))
for m in list(missing)[:10]:
    print('    MISSING: %s' % m)
if missing:
    sys.exit(1)
print('  OK: 导出集合完整覆盖')