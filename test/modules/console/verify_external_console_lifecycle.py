import ctypes,frida,json,pathlib,subprocess,sys,time
import verify_external_console as V
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
D=V.OUT;destination=D/((sys.argv[1] if len(sys.argv)>1 else 'lifecycle')+'.json');assert not destination.exists()
K=V.K;K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];K.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
p=V.pid();rows=[];records=[]
def helpers():return [x.pid for x in frida.get_local_device().enumerate_processes() if x.name.lower()=='hoi4_debug_console.exe']
def check(name,ok,detail=None):rows.append({'name':name,'ok':bool(ok),'details':detail});print(name,'PASS' if ok else 'FAIL',flush=True)
def cmd(text):r=V.command(p,text);records.append(r);return r
def stophelper(q):
 h=K.OpenProcess(0x100001,False,q);assert h;assert K.TerminateProcess(h,0);K.WaitForSingleObject(h,5000);K.CloseHandle(h)
initial=helpers();check('debug-auto-open-single',len(initial)==1,initial)
r=cmd('debugconsole');time.sleep(1);first=helpers();check('open-existing-is-idempotent',r['exit']==0 and first==initial,first)
stophelper(first[0]);r=cmd('help setcamheight');check('helper-termination-game-survives',r['exit']==0,r)
r=cmd('debugconsole');time.sleep(1);second=helpers();check('helper-reopen',r['exit']==0 and len(second)==1 and second!=first,second)
capture=[str(V.EXE),'--pid',str(p),'--logs-ms','1200'];r=subprocess.run(capture,capture_output=True,timeout=10);text=r.stdout.decode('utf-8',errors='replace');record={'command':capture,'stdout':text,'stderr':r.stderr.decode('utf-8',errors='replace'),'exit':r.returncode};records.append(record)
check('three-live-log-sources',r.returncode==0 and all('['+s+']' in text for s in ['GAME','ERROR','PLUGIN']),{'bytes':len(r.stdout)})
sys.path.insert(0,str(V.ROOT/'test/tools'));import hoi4_launch as H;H.kill()
end=time.monotonic()+6
while helpers() and time.monotonic()<end:time.sleep(.1)
check('helper-exits-with-game',not helpers(),helpers())
result={'rows':rows,'records':records,'checks':len(rows),'passed':sum(r['ok'] for r in rows),'ui_visual_verified':False,'window_close_button_tested':False};result['exit']=int(result['checks']!=result['passed']);destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','records']}));raise SystemExit(result['exit'])
