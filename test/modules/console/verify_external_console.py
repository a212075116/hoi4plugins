import argparse,concurrent.futures,ctypes,hashlib,json,pathlib,re,struct,subprocess,sys,time
import frida
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'test/reports/20261012_variable64_transaction/external_console'
EXE=ROOT/'build/Release/hoi4_debug_console.exe'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];K.CreateFileW.restype=ctypes.c_void_p
K.OpenThread.argtypes=[ctypes.c_ulong,ctypes.c_bool,ctypes.c_ulong];K.OpenThread.restype=ctypes.c_void_p
K.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_bool,ctypes.c_ulong];K.OpenProcess.restype=ctypes.c_void_p
for name in ['CloseHandle','SuspendThread','ResumeThread']:
 getattr(K,name).argtypes=[ctypes.c_void_p]
K.WriteFile.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
K.ReadFile.argtypes=K.WriteFile.argtypes
INVALID=ctypes.c_void_p(-1).value
def pid():return next(p.pid for p in frida.get_local_device().enumerate_processes() if p.name.lower()=='hoi4.exe')
def command(p,line):
 c=[str(EXE),'--pid',str(p),'--command',line];x=subprocess.run(c,capture_output=True,timeout=25)
 return {'command':c,'stdout':x.stdout.decode('utf-8',errors='replace'),'stderr':x.stderr.decode('utf-8',errors='replace'),'exit':x.returncode}
def raw(p,body,header=None):
 h=K.CreateFileW(r'\\.\pipe\hoi4-plugin-debug-v1-'+str(p),0xc0000000,0,None,3,0,None)
 if h==INVALID:raise RuntimeError('pipe open '+str(ctypes.get_last_error()))
 try:
  data=(header or struct.pack('<4I',0x31434448,1,77,len(body)))+body;n=ctypes.c_ulong()
  assert K.WriteFile(h,data,len(data),ctypes.byref(n),None)
  buffer=ctypes.create_string_buffer(28);ok=K.ReadFile(h,buffer,28,ctypes.byref(n),None)
  if not ok:return {'closed':True,'error':ctypes.get_last_error()}
  assert n.value==28
  m,v,i,length,status,success,thread=struct.unpack('<7I',buffer.raw)
  text=ctypes.create_string_buffer(length);assert not length or K.ReadFile(h,text,length,ctypes.byref(n),None)
  return {'id':i,'status':status,'ok':success,'thread':thread,'message':text.raw.decode('utf-8',errors='replace')}
 finally:K.CloseHandle(h)
JS=r'''
const b=Process.getModuleByName('hoi4.exe').base;
let calls=[],heaps={},released=0,aligned=0,depth={},forceGate=false;
let mgr=b.add(0x35e1a80).readPointer(), forced=[], yes=new NativeCallback(()=>1,'uint8',['pointer']);
for(const off of [144]){let obj=mgr.add(off).readPointer(),vt=obj.readPointer(),copy=Memory.alloc(24);copy.writeByteArray(vt.readByteArray(24));copy.add(16).writePointer(yes);forced.push({obj,vt,copy});}
Interceptor.attach(b.add(0x24b4d60),{onEnter(a){this.tid=Process.getCurrentThreadId();depth[this.tid]=(depth[this.tid]||0)+1;this.result=a[1];calls.push({tid:this.tid,argc:a[2].add(12).readS32()});},onLeave(){let m=this.result.add(8),cap=m.add(24).readU64().toNumber();if(cap>15){let x=m.readPointer();if(cap+1>=4096){x=x.sub(8).readPointer();aligned++;}heaps[x.toString()]=(heaps[x.toString()]||0)+1;}depth[this.tid]--;}});
Interceptor.attach(b.add(0x21c9b00),{onEnter(a){let key=a[0].toString();if(heaps[key]){released++;heaps[key]--;if(!heaps[key])delete heaps[key];}}});
rpc.exports={snapshot(){let obj=b.add(0x332f698).readPointer(),cam=obj.add(0x750).readPointer();return {rawDate:b.add(0x332f260).readPointer().add(0x468).readS32(),height:cam.add(0x69c).readFloat(),lower:cam.add(0x6d0).readS32(),upper:cam.add(0x6d4).readS32(),calls:calls.length,tids:[...new Set(calls.map(x=>x.tid))],heaps:Object.keys(heaps),released,aligned};},gate(on){forceGate=on;for(const f of forced)f.obj.writePointer(on?f.copy:f.vt);},calls(){return calls;}};
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('phase');a.add_argument('--stress',action='store_true');a.add_argument('--menu',action='store_true');args=a.parse_args()
 dest=OUT/(args.phase+'.json');assert not dest.exists(),'preserve phase'
 p=pid();records=[];rows=[]
 def check(name,ok,details=None):rows.append({'name':name,'ok':bool(ok),'details':details});print(name,'PASS' if ok else 'FAIL',flush=True)
 def run(line):r=command(p,line);records.append(r);return r
 basic=run('setcamheight 500')
 if args.phase.lower().startswith(('baseline','rollback')):
  check('no-external-bridge',basic['exit']==2 and 'Cannot connect' in basic['stdout'])
 elif args.menu:
  for line in ['help setcamheight','setcamheight 1234']:
   r=run(line);check('menu-cancel-'+line,r['exit']==3 and 'status=2' in r['stdout'] and 'cancelled before execution' in r['stdout'],r)
 else:
  check('camera-command',basic['exit']==0 and 'Camera Height is 500' in basic['stdout'],basic)
  tid=int(re.search(r'thread=(\d+)',basic['stdout'])[1]);s=frida.attach(p);sc=s.create_script(JS);sc.on('message',lambda m,d:print('FRIDA',m,flush=True));sc.load();initial=sc.exports_sync.snapshot()
  try:
   pause=run('gamespeed 0');check('paused-command',pause['exit']==0,pause)
   pausedDate=sc.exports_sync.snapshot()['rawDate']
   for line,code,text in [('help setcamheight',0,'Set camera height'),('sch "500"',0,'Camera Height is 500'),('dc_not_a_command',1,'Unknown command'),('setcamheight "500',3,'Invalid syntax'),('help '+ 'x '*9,3,'Invalid syntax'),('setcamheight ;whoami',1,'unchanged'),('event zzc.1',0,'')]:
    r=run(line);check(line,r['exit']==code and text in r['stdout'],r)
   end=time.monotonic()+8
   while time.monotonic()<end and abs(sc.exports_sync.snapshot()['height']-950.25)>.1:time.sleep(.1)
   check('event-native-result',abs(sc.exports_sync.snapshot()['height']-950.25)<.1)
   run('setcamheight 500');time.sleep(1)
   for name,data,hdr in [('nul',b'help\0bad',None),('newline',b'help\nbad',None),('utf8',b'help \xff',None),('bad-version',b'x',struct.pack('<4I',0x31434448,2,1,1)),('overflow',b'',struct.pack('<4I',0x31434448,1,1,2049)),('bad-magic',b'x',struct.pack('<4I',0,1,1,1))]:
    r=raw(p,data,hdr);check(name,r.get('closed') or r.get('status')==1,r)
   sc.exports_sync.gate(True)
   r=run('setcamheight 1234');check('native-permission-gate-injection',r['exit']==3 and 'External console commands are disabled in multiplayer.' in r['stdout'],r)
   sc.exports_sync.gate(False);r=run('setcamheight 500');check('gate-restored',r['exit']==0)
   thread=K.OpenThread(2,False,tid);assert thread
   assert K.SuspendThread(thread)!=0xffffffff
   try:
    r=run('setcamheight 1234');check('suspended-cancel-before-execution',r['exit']==3 and 'status=2' in r['stdout'],r)
   finally:K.ResumeThread(thread);K.CloseHandle(thread)
   time.sleep(1);check('cancel-does-not-run-later',abs(sc.exports_sync.snapshot()['height']-500)<.1)
   for j in range(5):
    r=run('help "setcamheight"');check('reconnect-'+str(j),r['exit']==0)
   if args.stress:
    start=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:bulk=list(pool.map(lambda j:command(p,'help' if j%12==0 else 'help setcamheight'),range(240)))
    records.extend(bulk);check('concurrent-240',all(r['exit']==0 for r in bulk),{'seconds':time.monotonic()-start,'success':sum(r['exit']==0 for r in bulk)})
   snap=sc.exports_sync.snapshot();check('paused-date-stable',snap['rawDate']==pausedDate,snap)
   check('game-thread-only',snap['tids']==[tid],snap)
   check('owned-result-heap-released',not snap['heaps'] and snap['released']>0 and (not args.stress or snap['aligned']>=20),snap)
   run('setcamheight '+str(initial['height']))
  finally:sc.exports_sync.gate(False);s.detach()
 result={'pid':p,'phase':args.phase,'rows':rows,'passed':sum(r['ok'] for r in rows),'checks':len(rows),'records':records,'dll_sha256':hashlib.sha256((ROOT.parent/'hoi4_mod_plugin.dll').read_bytes()).hexdigest()};result['exit']=int(result['passed']!=result['checks']);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['records','rows']},ensure_ascii=False));return result['exit']
if __name__=='__main__':raise SystemExit(main())
