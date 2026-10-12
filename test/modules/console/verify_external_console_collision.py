import ctypes,json,pathlib,subprocess,sys,threading,time
import verify_external_console as V
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
out=V.OUT/'endpoint_collision.json';assert not out.exists()
K=V.K
class Startup(ctypes.Structure):
 _fields_=[('cb',ctypes.c_ulong),('reserved',ctypes.c_void_p),('desktop',ctypes.c_void_p),('title',ctypes.c_void_p),('x',ctypes.c_ulong),('y',ctypes.c_ulong),('width',ctypes.c_ulong),('height',ctypes.c_ulong),('charsX',ctypes.c_ulong),('charsY',ctypes.c_ulong),('fill',ctypes.c_ulong),('flags',ctypes.c_ulong),('show',ctypes.c_ushort),('reservedBytes',ctypes.c_ushort),('reserved2',ctypes.c_void_p),('stdin',ctypes.c_void_p),('stdout',ctypes.c_void_p),('stderr',ctypes.c_void_p)]
class Process(ctypes.Structure):
 _fields_=[('process',ctypes.c_void_p),('thread',ctypes.c_void_p),('pid',ctypes.c_ulong),('tid',ctypes.c_ulong)]
K.CreateProcessW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_bool,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.POINTER(Startup),ctypes.POINTER(Process)]
K.CreateNamedPipeW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];K.CreateNamedPipeW.restype=ctypes.c_void_p
K.ConnectNamedPipe.argtypes=[ctypes.c_void_p,ctypes.c_void_p];K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];K.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
sys.path.insert(0,str(V.ROOT/'test/tools'));import hoi4_launch as H;H.kill();H.clear_log()
si=Startup();si.cb=ctypes.sizeof(si);pi=Process();args='"'+str(V.ROOT.parent/'hoi4.exe')+'" -gdpr-compliant -nolauncher -debug -no-plugin-console';cmd=ctypes.create_unicode_buffer(args)
assert K.CreateProcessW(str(V.ROOT.parent/'hoi4.exe'),cmd,None,None,False,4,None,str(V.ROOT.parent),ctypes.byref(si),ctypes.byref(pi)),ctypes.get_last_error()
h=K.CreateNamedPipeW(r'\\.\pipe\hoi4-plugin-debug-v1-'+str(pi.pid),0x00080003,0,4,4096,4096,5000,None);assert h!=V.INVALID,ctypes.get_last_error()
t=threading.Thread(target=lambda:K.ConnectNamedPipe(h,None),daemon=True);t.start();records=[];rows=[]
try:
 assert K.ResumeThread(pi.thread)!=0xffffffff
 end=time.monotonic()+35
 while 'pipe creation failed' not in H.read_log() and time.monotonic()<end:time.sleep(.1)
 rows.append({'name':'preexisting-endpoint-fails-closed','ok':'[debugconsole] pipe creation failed error=5' in H.read_log()})
 r=V.command(pi.pid,'setcamheight 500');records.append(r);rows.append({'name':'client-rejects-wrong-server-pid','ok':r['exit']==2 and 'Cannot connect' in r['stdout']})
 code=ctypes.c_ulong();assert K.GetExitCodeProcess(pi.process,ctypes.byref(code));rows.append({'name':'game-survives-collision','ok':code.value==259,'exit_code':code.value})
finally:
 K.TerminateProcess(pi.process,0);K.CloseHandle(pi.thread);K.CloseHandle(pi.process);K.CloseHandle(h);t.join(2)
r={'rows':rows,'records':records,'plugin_log':H.read_log(),'checks':len(rows),'passed':sum(x['ok'] for x in rows),'game_visual_verified':False};r['exit']=int(r['checks']!=r['passed']);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k not in ['records','plugin_log']},ensure_ascii=False));raise SystemExit(r['exit'])
