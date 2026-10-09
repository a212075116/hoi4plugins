# -*- coding: utf-8 -*-
# idalib_cli.py -- 向 idalib_server 发请求
#
# 两种用法:
#   1) 命令行: python idalib_cli.py decompile 0x140DC53B0 [lines]
#   2) 作为模块: from idalib_cli import send;  send({'op':'ping'})
#
# 连接策略 (重要):
#   服务端 session() 是 while True 循环, 支持在同一连接上连续收发。
#   早期版本每个请求都 create_connection + close, 在做全量扫描 (12 万次请求) 时
#   把 Windows 的临时端口耗尽, 报 WinError 10048。现在复用一条持久连接,
#   出错或对端关闭时才重连。
import socket, json, sys, os, threading

PORT = int(os.environ.get('IDALIB_PORT', '19531'))

_lock = threading.Lock()
_conn = None
_file = None


def _connect(timeout):
    global _conn, _file
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
    _conn = socket.create_connection(('127.0.0.1', PORT), timeout=timeout)
    _conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    _file = _conn.makefile('rwb')


def send(req, timeout=600):
    """发一条请求, 返回解析后的 dict。复用持久连接。"""
    global _conn, _file
    payload = (json.dumps(req, ensure_ascii=False) + chr(10)).encode('utf-8')
    with _lock:
        for attempt in (0, 1):
            try:
                if _conn is None:
                    _connect(timeout)
                _file.write(payload)
                _file.flush()
                line = _file.readline()
                if not line:
                    raise ConnectionError('服务端关闭了连接')
                return json.loads(line.decode('utf-8'))
            except Exception as e:
                # 连接坏了就重建一次; 第二次仍失败则抛出
                try:
                    if _conn is not None:
                        _conn.close()
                except Exception:
                    pass
                _conn = None
                _file = None
                if attempt == 1:
                    return {'ok': False, 'err': '连接失败: %s' % e}
    return {'ok': False, 'err': 'unreachable'}


def close():
    global _conn, _file
    with _lock:
        try:
            if _conn is not None:
                _conn.close()
        except Exception:
            pass
        _conn = None
        _file = None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    op = sys.argv[1]
    args = sys.argv[2:]
    req = {'op': op}
    if op in ('decompile',):
        req['ea'] = args[0]
        if len(args) > 1:
            req['lines'] = int(args[1])
    elif op in ('disasm',):
        req['ea'] = args[0]
        if len(args) > 1:
            req['count'] = int(args[1])
        if len(args) > 2:
            req['back'] = int(args[2])
    elif op in ('xrefs_to', 'func', 'vtable', 'bytes', 'read_str'):
        req['ea'] = args[0]
        if len(args) > 1:
            req['max' if op == 'vtable' else 'n'] = int(args[1])
    elif op in ('strings', 'names', 'grep_disasm'):
        req['pattern' if op == 'grep_disasm' else 'needle'] = args[0]
        if len(args) > 1:
            req['limit'] = int(args[1])
    r = send(req)
    print(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
