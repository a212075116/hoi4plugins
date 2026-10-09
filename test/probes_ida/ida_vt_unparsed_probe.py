# -*- coding: utf-8 -*-
import os, json, re, traceback
import ida_pro, ida_auto, ida_name
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
VT_RE = re.compile(r'^\?\?_7(.+?)@@6B@(_\d+)?$')
DEM_RE = re.compile(r'^(?:const |volatile )*(.+?)::`vftable\'$')
try:
    ida_auto.auto_wait()
    n = ida_name.get_nlist_size()
    syms = []
    for i in range(n):
        nm = ida_name.get_nlist_name(i)
        if nm and nm.startswith('??_7'):
            syms.append(nm)
    w('total=%d' % len(syms))
    bad = []
    for s in syms:
        m = VT_RE.match(s)
        if not m:
            bad.append(('VT_RE', s)); continue
        try:
            d = ida_name.demangle_name(s, ida_name.MNG_SHORT_FORM)
        except Exception:
            d = None
        if not d:
            bad.append(('DEMANGLE_NONE', s)); continue
        if not DEM_RE.match(d):
            bad.append(('DEM_RE:' + d, s))
    w('bad=%d' % len(bad))
    w('\n--- first 40 bad ---')
    for why, s in bad[:40]:
        w('  [%s] %s' % (why[:60], s))
    w('\n--- suffix histogram of bad syms ---')
    import collections
    c = collections.Counter()
    for why, s in bad:
        c[s[-14:]] += 1
    for k, v in c.most_common(15):
        w('  %-16s %d' % (k, v))
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)