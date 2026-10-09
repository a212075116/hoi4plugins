# -*- coding: utf-8 -*-
# idalib_cli.py -- 向 idalib_server 发一条请求并打印结果
# 用法: python flirt/idalib_cli.py decompile 0x140DC53B0 [lines]
#       python flirt/idalib_cli.py xrefs_to 0x1427298e0
#       python flirt/idalib_cli.py strings debug_zoom
#       python flirt/idalib_cli.py names CCamera
#       python flirt/idalib_cli.py vtable 0x142a27e08
#       python flirt/idalib_cli.py disasm 0x14000bbcd 40 20
#       python flirt/idalib_cli.py grep_disasm +6D0h
#       python flirt/idalib_cli.py func 0x140DC53B0
#       python flirt/idalib_cli.py ping
import socket, json, sys, os
PORT = int(os.environ.get('IDALIB_PORT', '19531'))

def send(req, timeout=600):
    s = socket.create_connection(('127.0.0.1', PORT), timeout=timeout)
    s.sendall((json.dumps(req, ensure_ascii=False) + chr(10)).encode('utf-8'))
    f = s.makefile('rb')
    line = f.readline()
    s.close()
    if not line: return {'ok': False, 'err': '服务无响应(可能还在加载 .i64)'}
    return json.loads(line.decode('utf-8'))

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    op = sys.argv[1]
    args = sys.argv[2:]
    req = {'op': op}
    if op in ('decompile',):
        req['ea'] = args[0]
        if len(args) > 1: req['lines'] = int(args[1])
    elif op in ('disasm',):
        req['ea'] = args[0]
        if len(args) > 1: req['count'] = int(args[1])
        if len(args) > 2: req['back'] = int(args[2])
    elif op in ('xrefs_to', 'func', 'vtable', 'bytes', 'read_str'):
        req['ea'] = args[0]
        if len(args) > 1: req['max' if op == 'vtable' else 'n'] = int(args[1])
    elif op in ('strings', 'names', 'grep_disasm'):
        req['pattern' if op == 'grep_disasm' else 'needle'] = args[0]
        if len(args) > 1: req['limit'] = int(args[1])
    r = send(req)
    print(json.dumps(r, indent=1, ensure_ascii=False))

if __name__ == '__main__':
    main()
