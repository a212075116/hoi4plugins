import idc, idautils, ida_segment, idaapi
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/reports/ida_dmp_info.txt'
f = open(OUT, 'w', encoding='utf-8')
def w(s):
    try: f.write(str(s) + chr(10))
    except: pass
try: w('file: ' + idaapi.get_input_file_path())
except Exception as e: w('file: ERR ' + str(e))
w('')
w('=== segments ===')
try:
    n = 0
    for s in idautils.Segments():
        sg = ida_segment.getseg(s)
        nm = ida_segment.get_segm_name(sg)
        w('  %s  start=0x%X end=0x%X size=0x%X' % (nm, sg.start_ea, sg.end_ea, sg.end_ea - sg.start_ea))
        n += 1
        if n > 40: w('  ...'); break
except Exception as e: w('segments ERR ' + str(e))
w('')
w('=== names with Thread/Exception/Crash ===')
try:
    c = 0
    for ea, nm in idautils.Names():
        low = nm.lower()
        if 'exception' in low or 'thread' in low or 'crash' in low:
            w('  0x%X  %s' % (ea, nm))
            c += 1
            if c > 60: break
    w('  total shown: %d' % c)
except Exception as e: w('names ERR ' + str(e))
w('')
w('=== all names (first 60) ===')
try:
    c = 0
    for ea, nm in idautils.Names():
        w('  0x%X  %s' % (ea, nm))
        c += 1
        if c > 60: break
except Exception as e: w('allnames ERR ' + str(e))
f.close()
idc.qexit(0)
