# -*- coding: utf-8 -*-
# idalib_server.py -- IDA 9.0 idalib 常驻服务 (进程内驱动, 免去每次 idat.exe 的 3-5 分钟冷启动)
#
# 为什么: idat.exe 每次批处理要重新加载 906MB 的 .i64 并 auto_wait, 实测 3-5 分钟;
#          idalib 是进程内库, 加载一次后所有查询都是毫秒级。
# 用法:
#   python flirt/idalib_server.py            # 后台常驻, 监听 127.0.0.1:PORT
#   python flirt/idalib_cli.py decompile 0x140DC53B0
#
# 协议: 一行一个 JSON 请求 -> 一行一个 JSON 响应
#   {'op':'ping'}
#   {'op':'decompile','ea':'0x...', 'lines':400}
#   {'op':'disasm','ea':'0x...','count':40}
#   {'op':'xrefs_to','ea':'0x...'}
#   {'op':'func','ea':'0x...'}
#   {'op':'strings','needle':'...','limit':50}
#   {'op':'names','needle':'...','limit':50}
#   {'op':'vtable','ea':'0x...','max':40}
#   {'op':'search_imm','seg_code':true,'pattern':'+6D0h','limit':50}
#   {'op':'shutdown'}
import os, sys, json, socket, threading, traceback

IDADIR = os.environ.get('IDADIR_OVERRIDE', r'D:\IDA Professional 9.0')
os.environ['IDADIR'] = IDADIR

I64 = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/sources/1.19.3/hoi4.exe.i64'
PORT = int(os.environ.get('IDALIB_PORT', '19531'))

import idapro
t0 = __import__('time').time()
print('[idalib] open_database ...', flush=True)
rc = idapro.open_database(I64, False)
print('[idalib] open rc=%s  用时 %.1fs' % (rc, __import__('time').time() - t0), flush=True)

import idaapi, idautils, ida_funcs, ida_name, ida_hexrays, ida_bytes, ida_segment, ida_nalt, idc
ida_hexrays.init_hexrays_plugin()
BASE = idaapi.get_imagebase()
print('[idalib] imagebase=%#x  hexrays=%s' % (BASE, ida_hexrays.init_hexrays_plugin()), flush=True)


def ev(v):
    if v is None: return None
    if isinstance(v, str):
        return int(v, 16) if v.startswith('0x') else int(v)
    return int(v)


def op_ping(req):
    return {'ok': True, 'imagebase': hex(BASE), 'funcs': ida_funcs.get_func_qty()}


def op_decompile(req):
    ea = ev(req['ea'])
    n = int(req.get('lines', 300))
    try:
        cf = ida_hexrays.decompile(ea)
        if not cf: return {'ok': False, 'err': 'decompile 无结果'}
        s = str(cf).split(chr(10))
        return {'ok': True, 'ea': hex(ea), 'total_lines': len(s), 'text': chr(10).join(s[:n])}
    except Exception as e:
        return {'ok': False, 'err': str(e)}


def op_disasm(req):
    ea = ev(req['ea']); cnt = int(req.get('count', 40)); back = int(req.get('back', 0))
    lines = []
    cur = ea - back * 8
    for _ in range(cnt + back):
        try: lines.append('%#x  %s' % (cur, idc.GetDisasm(cur)))
        except Exception: break
        nxt = idc.next_head(cur, cur + 16)
        if nxt <= cur: break
        cur = nxt
    return {'ok': True, 'lines': lines}


def op_xrefs_to(req):
    ea = ev(req['ea'])
    out = []
    for x in idautils.XrefsTo(ea, 0):
        f = ida_funcs.get_func(x.frm)
        out.append({'from': hex(x.frm), 'type': int(x.type),
                    'func': ida_funcs.get_func_name(f.start_ea) if f else None,
                    'func_size': (f.end_ea - f.start_ea) if f else None})
    return {'ok': True, 'count': len(out), 'refs': out}


def op_func(req):
    ea = ev(req['ea'])
    f = ida_funcs.get_func(ea)
    if not f: return {'ok': False, 'err': '不在函数内'}
    return {'ok': True, 'start': hex(f.start_ea), 'end': hex(f.end_ea),
            'size': f.end_ea - f.start_ea, 'name': ida_funcs.get_func_name(f.start_ea)}


def op_strings(req):
    nd = req['needle']; lim = int(req.get('limit', 50))
    out = []
    for s in idautils.Strings():
        v = str(s)
        if nd in v:
            out.append({'ea': hex(s.ea), 's': v[:300]})
            if len(out) >= lim: break
    return {'ok': True, 'count': len(out), 'items': out}


def op_names(req):
    nd = req['needle']; lim = int(req.get('limit', 50))
    out = []
    n = ida_name.get_nlist_size()
    for i in range(n):
        s = ida_name.get_nlist_name(i)
        if s and nd in s:
            out.append({'ea': hex(ida_name.get_nlist_ea(i)), 'name': s})
            if len(out) >= lim: break
    return {'ok': True, 'count': len(out), 'items': out}


def op_vtable(req):
    ea = ev(req['ea']); mx = int(req.get('max', 40))
    out = []; k = 0
    while k < mx:
        p = ida_bytes.get_qword(ea + k * 8)
        seg = ida_segment.getseg(p)
        if p == 0 or seg is None or not (seg.perm & 1): break
        out.append({'i': k, 'off': hex(k * 8), 'fn': hex(p), 'name': ida_name.get_name(p) or ''})
        k += 1
    return {'ok': True, 'count': k, 'slots': out}


def op_bytes(req):
    ea = ev(req['ea']); n = int(req.get('n', 64))
    b = ida_bytes.get_bytes(ea, n)
    return {'ok': True, 'hex': b.hex() if b else None}


def op_read_str(req):
    ea = ev(req['ea']); n = int(req.get('n', 300))
    b = ida_bytes.get_bytes(ea, n)
    if not b: return {'ok': False, 'err': '不可读'}
    return {'ok': True, 's': b.split(b'\x00')[0].decode('ascii', 'replace')}


def op_grep_disasm(req):
    """在全部函数的反汇编文本里搜子串, 返回命中所在函数"""
    pat = req['pattern']; lim = int(req.get('limit', 60))
    only_small = bool(req.get('only_small', False))
    hits = {}
    qty = ida_funcs.get_func_qty()
    scanned = 0
    for i in range(qty):
        f = ida_funcs.getn_func(i)
        if f is None: continue
        sz = f.end_ea - f.start_ea
        if only_small and sz > 40000: continue
        scanned += 1
        found = None
        for item in idautils.FuncItems(f.start_ea):
            d = idc.GetDisasm(item)
            if pat in d:
                found = (item, d)
                hits.setdefault(f.start_ea, []).append((item, d))
        if found and len(hits) >= lim: break
    return {'ok': True, 'scanned_funcs': scanned, 'count': len(hits),
            'items': [{'func': ida_funcs.get_func_name(k), 'func_ea': hex(k), 'size': (ida_funcs.get_func(k).end_ea - k) if ida_funcs.get_func(k) else None,
                       'hits': [{'ea': hex(a), 'd': d} for a, d in v[:6]]} for k, v in hits.items()]}


OPS = {'ping': op_ping, 'decompile': op_decompile, 'disasm': op_disasm, 'xrefs_to': op_xrefs_to,
       'func': op_func, 'strings': op_strings, 'names': op_names, 'vtable': op_vtable,
       'bytes': op_bytes, 'read_str': op_read_str, 'grep_disasm': op_grep_disasm}


def handle(req):
    op = req.get('op')
    if op == 'shutdown':
        return {'ok': True, 'bye': True}
    fn = OPS.get(op)
    if fn is None:
        return {'ok': False, 'err': '未知 op: %r (可用: %s)' % (op, ','.join(sorted(OPS)))}
    try:
        return fn(req)
    except Exception:
        return {'ok': False, 'err': traceback.format_exc()[:1200]}


def serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', PORT))
    srv.listen(8)
    print('[idalib] 监听 127.0.0.1:%d  就绪' % PORT, flush=True)
    while True:
        conn, addr = srv.accept()
        # 注意: IDA 的 API 只能从主线程调用, 所以这里必须串行处理, 不能开子线程
        try:
            session(conn)
        except Exception as e:
            print('[idalib] session 异常: %s' % e, flush=True)
        finally:
            try: conn.close()
            except Exception: pass


def session(conn):
    f = conn.makefile('rwb')
    while True:
        line = f.readline()
        if not line: break
        try:
            req = json.loads(line.decode('utf-8'))
        except Exception as e:
            f.write((json.dumps({'ok': False, 'err': 'JSON 解析失败: %s' % e}) + chr(10)).encode('utf-8')); f.flush(); continue
        if req.get('op') == 'shutdown':
            f.write((json.dumps({'ok': True, 'bye': True}) + chr(10)).encode('utf-8')); f.flush()
            print('[idalib] shutdown 请求, 退出', flush=True)
            os._exit(0)
        resp = handle(req)
        f.write((json.dumps(resp, ensure_ascii=False) + chr(10)).encode('utf-8'))
        f.flush()


if __name__ == '__main__':
    serve()
