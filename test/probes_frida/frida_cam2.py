# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable
W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_摄像机对象定位与字段.txt'
pid, session, sc, fresh = connect(W + '/flirt/loader/_cam2.js', tag='cam2')
wait_stable(sc, tag='cam2')
r = sc.exports_sync.probe()
print(json.dumps({k: v for k, v in r.items() if k != 'dump'}, indent=1, ensure_ascii=False))
L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 定位摄像机状态对象, 验证 debug_zoom 写入的 +0x6D0/+0x6D4 字段')
A('静态依据   : sub_140250340 (debug_zoom 处理函数) 把 (*(vt+0x130))(qword_14332F698) 的 +0x6D0 置 0, +0x6D4 置 1200')
A('完整性     : 全量输出, 不抽样')
A('')
for k in ['ok', 'gsSlot', 'obj', 'vt', 'vtRva', 'getter', 'getterRva', 'cam', 'camVt', 'camVtRva', 'i0x6d0', 'i0x6d4', 'b0x6f0', 'f0x6d0', 'f0x6d4', 'err']:
    if k in r: A('%-12s = %s' % (k, r[k]))
A('')
A('=== 摄像机对象 +0x600..+0x820 十六进制(全量) ===')
for ln in (r.get('dump') or []): A('  ' + ln)
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)))
print('')
for ln in (r.get('dump') or []): print(ln)
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
