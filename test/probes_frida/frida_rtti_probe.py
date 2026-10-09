# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frida_host import connect, wait_stable

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
OUT = W + '/reports/20261009_015321_原版_RTTI命名读取验证.txt'
pid, session, sc, fresh = connect(W + '/flirt/loader/_rtti_probe.js', tag='rtti')
wait_stable(sc, tag='rtti')

CORE = [
  (0x27E7360, 'CCountry'), (0x2936CC0, 'CState'), (0x2936D10, 'CState_b'),
  (0x2971B18, 'CProvince'), (0x2971B68, 'CProvince_b'),
  (0x297EA60, 'CCharacter'),
  (0x2962A18, 'CFleet'), (0x2962A70, 'CFleet_b'),
  (0x2957F28, 'CShip'), (0x2957F90, 'CShip_b'),
  (0x2962F70, 'CTaskForce'), (0x2963150, 'CTaskForce_b'), (0x29631C0, 'CTaskForce_c'), (0x2963208, 'CTaskForce_d'),
  (0x295A2B0, 'CArmy'), (0x295A490, 'CArmy_b'), (0x295A500, 'CArmy_c'), (0x295A548, 'CArmy_d'),
  (0x29530D8, 'CUnit'), (0x29532B0, 'CUnit_b'), (0x2953320, 'CUnit_c'),
  (0x27210E0, 'CGameState'), (0x2721138, 'CGameState_b'),
  (0x27183A8, 'CGameDate'), (0x27183D8, 'CGameDate_b'),
]

L = []
def A(s): L.append(str(s))
A('时间戳     : 20261009_015321')
A('测试模块   : 游戏根目录 hoi4.exe  (原版环境)')
A('附加方式   : %s' % ('新开进程' if fresh else 'attach 已有进程 pid=%s' % pid))
A('测试目的   : 用运行时 RTTI 交叉验证 IDA 静态分析给出的虚表命名是否正确')
A('原理       : vftable 的 -0x8 是 RTTICompleteObjectLocator(COL);')
A('             COL+0x0C 是 pTypeDescriptor 的 RVA; TYPE_DESCRIPTOR+0x10 是类名字符串;')
A('             COL+0x10 是 pClassHierarchyDescriptor 的 RVA, 其 +0x0C 指向 base class array,')
A('             数组每项 -4 偏移指向 BaseClassDescriptor, 其 +0x00 又是 pTypeDescriptor 的 RVA。')
A('完整性     : 全量输出, 不抽样')
A('')
res = sc.exports_sync.many([r for r, _ in CORE])
ok = 0; bad = 0
A('%-10s %-16s %-34s %-8s %-10s %s' % ('IDA假定名', 'RVA', '运行时RTTI真名', 'COL签名', '偏移', '基类链'))
for (rva, guess), r in zip(CORE, res):
    if r.get('ok') and r.get('name'):
        ok += 1
        A('%-10s %-16s %-34s %-8s %-10s %s' % (guess, hex(rva), r['name'], r.get('sig'), r.get('offset'), ' <- '.join(r.get('bases') or [])))
    else:
        bad += 1
        A('%-10s %-16s %-34s %-8s %-10s %s' % (guess, hex(rva), '读取失败: %s' % r.get('err'), r.get('sig'), '', ''))
A('')
A('读取成功 %d / %d, 失败 %d' % (ok, len(CORE), bad))
A('')
A('--- 与 IDA 符号名的对照判定 ---')
A('IDA 的符号名形如 ??_7<类名>@@6B@ (vftable) 与 ??_R4<类名>@@6B@ (COL)。')
A('运行时读出的名字是 TYPE_DESCRIPTOR 里的裸类名(不带 ??_7 前缀与 @@6B@ 后缀)。')
A('判定规则: 把 IDA 的 ??_7X@@6B@ 去壳得到 X, 与运行时名字逐字符比较。')
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s 行数=%d' % (OUT, len(L)), flush=True)
print('')
for (rva, guess), r in zip(CORE, res):
    print('%-16s %-16s -> %-30s bases=%s' % (guess, hex(rva), (r.get('name') if r.get('ok') else ('ERR ' + str(r.get('err')))), (r.get('bases') or [])[:4]))
session.detach()
print('[游戏保持运行 pid=%s]' % pid)
