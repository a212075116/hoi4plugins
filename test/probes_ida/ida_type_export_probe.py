# -*- coding: utf-8 -*-
# 正解：parse_decls 建类型 -> print_decls 导出头文件
import os, json, traceback
import ida_pro, ida_auto, ida_typeinf
cfg = json.load(open(os.environ['FLIRT_JOB'], 'r', encoding='utf-8'))
f = open(cfg['output'], 'w', encoding='utf-8')
def w(s):
    f.write(str(s) + '\n'); f.flush()
try:
    ida_auto.auto_wait()
    til = ida_typeinf.get_idati()
    w('idati = %s' % (til is not None))
    w('')
    # ---- 步骤1: parse_decls 定义类型 ----
    src = '''
struct CUnitVtbl0 {
    void *__vfunc_0;
    void *__vfunc_1;
};
struct CUnit {
    CUnitVtbl0 *__vftable_0;
    int pad_08;
    void *__vftable_10;
    char pad_18[0xA0];
    void *__vftable_B8;
    int field_140;
};
'''
    w('步骤1: parse_decls 定义 CUnit / CUnitVtbl0')
    errs = ida_typeinf.parse_decls(til, src, None, 0)
    w('  返回错误数 = %d  (0 表示成功)' % errs)
    w('')
    # ---- 步骤2: 验证类型真的进了 til ----
    w('步骤2: get_named_type 验证')
    for nm in ['CUnit', 'CUnitVtbl0']:
        r = ida_typeinf.get_named_type(til, nm, 0)
        w('  %-12s -> %s' % (nm, (r[1] if r else '<未找到>')))
    w('')
    # ---- 步骤3: print_decls 导出为头文件 ----
    w('步骤3: print_decls 导出头文件')
    collected = []
    def printer(text):
        collected.append(text)
    for label, flags in [
        ('0 (默认)', 0),
        ('PDF_HEADER_CMT', ida_typeinf.PDF_HEADER_CMT),
    ]:
        collected.clear()
        n = ida_typeinf.print_decls(printer, til, None, flags)
        body = ''.join(collected)
        w('  --- flags=%s  返回=%d  文本长度=%d ---' % (label, n, len(body)))
        w('  前 1600 字符:')
        w(body[:1600])
        w('')
except Exception:
    w('EXC ' + traceback.format_exc())
f.close()
ida_pro.qexit(0)