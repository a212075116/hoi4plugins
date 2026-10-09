# -*- coding: utf-8 -*-
"""扫描 hoi4.exe 全部虚表, 建立 类名 -> 虚表 -> 槽位 索引表。

RTTI 读取要点 (本项目实测, 见 ai_docs/07_逆向能力/虚表与RTTI.md):
  COL 位于 vftable-8
  COL +0x00 = signature (必须 == 1)
  COL +0x0C = uint32 RVA -> TypeDescriptor
  COL +0x10 = uint32 RVA -> ClassHierarchyDescriptor
  TypeDescriptor +0x10 = 类名 (格式 .?AV<Name>@@)
  ** 指针字段是 4 字节 RVA, 不是标准 x64 的 8 字节绝对地址 **

输出 JSON: 每个虚表 { rva, sym, cls, nbase, n, slots[] }
"""
import sys, json, io, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + '..' + os.sep + 'tools')
from idalib_cli import send

# IMG / MAX_EA 不写死: 启动时向服务端 ping 取得 (见 init_range)
IMG = None
MAX_EA = None


def init_range():
    """从 idalib 服务取 imagebase 与地址上界, 避免硬编码。"""
    global IMG, MAX_EA
    r = send({'op': 'ping'})
    if not r.get('ok'):
        raise SystemExit('idalib 服务不可用: %s' % r)
    IMG = int(r['imagebase'], 16)
    MAX_EA = int(r.get('max_ea') or (IMG + 0x4000000), 16)
    print('      imagebase = %#x   max_ea = %#x   funcs = %s'
          % (IMG, MAX_EA, r.get('funcs')), flush=True)
    print('      数据库 = %s' % r.get('input'), flush=True)


def bytes_at(ea, n):
    r = send({'op': 'bytes', 'ea': hex(ea), 'n': n})
    h = r.get('hex')
    return bytes.fromhex(h) if h else None


def u32(ea):
    d = bytes_at(ea, 4)
    return int.from_bytes(d, 'little') if d and len(d) == 4 else None


def q64(ea):
    d = bytes_at(ea, 8)
    return int.from_bytes(d, 'little') if d and len(d) == 8 else None


def read_str(ea, n=200):
    r = send({'op': 'read_str', 'ea': hex(ea), 'n': n})
    return r.get('s') if r.get('ok') else None


def parse_class_name(raw):
    if not raw:
        return None
    if raw.startswith('.?AV') or raw.startswith('.?AU'):
        body = raw[4:]
        if body.endswith('@@'):
            body = body[:-2]
        return body
    return None


def rtti_of(vt_ea):
    col = q64(vt_ea - 8)
    if not col or not (IMG <= col < MAX_EA):
        return None, None
    if u32(col) != 1:
        return None, None
    td_rva = u32(col + 0x0C)
    cd_rva = u32(col + 0x10)
    if not td_rva or not cd_rva:
        return None, None
    td = IMG + td_rva
    cd = IMG + cd_rva
    if not (IMG <= td < MAX_EA) or not (IMG <= cd < MAX_EA):
        return None, None
    cls = parse_class_name(read_str(td + 0x10))
    nbase = u32(cd + 0x08)
    if cls is None or nbase is None or nbase > 64:
        return None, None
    return cls, nbase


def slots_of(vt_ea, limit=64):
    """一次读 n*8 字节, 再逐个判定; 避免每个槽一次 RPC"""
    raw = bytes_at(vt_ea, limit * 8)
    if not raw:
        return []
    out = []
    for i in range(0, len(raw) - 7, 8):
        p = int.from_bytes(raw[i:i + 8], 'little')
        if not p or not (IMG <= p < MAX_EA):
            break
        out.append(p)
    return out


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'vt_index.json'
    only_n = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    t0 = time.time()
    print('[0/3] 探测服务与镜像范围 ...', flush=True)
    init_range()
    print('[1/3] 取 ??_7 符号 ...', flush=True)
    r = send({'op': 'names', 'needle': '??_7', 'limit': 100000})
    items = r.get('items') or []
    print('      共 %d 个, 用时 %.1fs' % (len(items), time.time() - t0), flush=True)
    if only_n:
        items = items[:only_n]
        print('      [试跑模式] 只处理前 %d 个' % only_n, flush=True)

    print('[2/3] 解析 RTTI 与槽位 ...', flush=True)
    result = []
    ok_rtti = 0
    t1 = time.time()
    for idx, it in enumerate(items):
        if idx and idx % 500 == 0:
            el = time.time() - t1
            eta = el / idx * (len(items) - idx)
            print('      %d/%d  rtti_ok=%d  已用%.0fs  预计剩余%.0fs'
                  % (idx, len(items), ok_rtti, el, eta), flush=True)
        ea = int(it['ea'], 16)
        cls, nbase = rtti_of(ea)
        if cls:
            ok_rtti += 1
        slots = slots_of(ea)
        result.append({
            'rva': ea - IMG,
            'sym': it['name'],
            'cls': cls,
            'nbase': nbase,
            'n': len(slots),
            'slots': [s - IMG for s in slots],
        })

    print('[3/3] 写出 ...', flush=True)
    doc = {
        'imagebase': IMG,
        'game': 'hoi4.exe 1.19.3',
        'note': 'RTTI 指针字段是 4 字节 RVA; cls 由 RTTI 反查, sym 来自 IDA 符号',
        'count': len(result),
        'rtti_ok': ok_rtti,
        'vt': result,
    }
    with io.open(out_path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    print('完成: %d 个虚表, RTTI 成功 %d, 总用时 %.1fs'
          % (len(result), ok_rtti, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
