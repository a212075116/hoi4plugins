import collections,ctypes,hashlib,json,os,pathlib,queue,re,statistics,subprocess,sys,threading,time
import frida
ROOT=pathlib.Path(__file__).resolve().parents[3];D=ROOT/'test/reports/20261012_variable64_transaction/console_stress'
sys.path.insert(0,str(ROOT/'test/tools'));import hoi4_launch as H
sys.path.insert(0,str(ROOT/'test/modules/console'));import verify_external_console as V
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
K=V.K;K.GetProcessHandleCount.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
class PM(ctypes.Structure):
 _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['peak','working','peakPaged','paged','peakNonpaged','nonpaged','pagefile','peakPagefile','private']]
P=ctypes.WinDLL('psapi');P.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(PM),ctypes.c_ulong]
K.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4
K.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
def resources(pid):
 h=K.OpenProcess(0x101410,False,pid)
 if not h:return None
 try:
  p=PM();p.cb=ctypes.sizeof(p);count=ctypes.c_ulong();a,b,c,d=[ctypes.c_ulonglong() for _ in range(4)]
  if not P.GetProcessMemoryInfo(h,ctypes.byref(p),p.cb):return None
  K.GetProcessHandleCount(h,ctypes.byref(count));K.GetProcessTimes(h,ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d))
  return {'private':p.private,'working':p.working,'handles':count.value,'cpu_seconds':(c.value+d.value)/1e7}
 finally:K.CloseHandle(h)
def percentile(a,p):return sorted(a)[min(len(a)-1,int((len(a)-1)*p))] if a else None
class Session:
 def __init__(self,pid,fixture):
  self.process=subprocess.Popen([str(ROOT.parent/'hoi4_debug_console.exe'),'--pid',str(pid),'--session-stdio','--log-dir',str(fixture)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  self.results=queue.Queue();self.local=threading.Event();self.lines=collections.Counter();self.line_errors=[];self.log_counts=collections.Counter();self.raw=(D/'session_stdout.log').open('wb');self.err=(D/'session_stderr.log').open('wb')
  def reader():
   for line in iter(self.process.stdout.readline,b''):
    self.raw.write(line)
    if b'[LOCAL]' in line:self.local.set()
    m=re.search(rb'\[RESULT id=(\d+) status=(\d+) ok=(\d+) thread=(\d+)\]',line)
    if m:self.results.put({'id':int(m[1]),'status':int(m[2]),'ok':int(m[3]),'thread':int(m[4]),'message':line.decode('utf-8',errors='replace').strip()})
    m=re.search(rb'\[(GAME|ERROR|PLUGIN)\] SEQ:(\d+) ',line)
    if m:
     src=m[1].decode();n=int(m[2]);expected=self.log_counts[src]
     if n!=expected:self.line_errors.append({'source':src,'expected':expected,'observed':n})
     self.log_counts[src]=n+1
   self.raw.flush()
  self.reader=threading.Thread(target=reader,daemon=True);self.reader.start()
 def send(self,line):self.process.stdin.write(line.encode()+b'\n');self.process.stdin.flush()
 def command(self,line,timeout=8):
  start=time.monotonic();self.send(line);r=self.results.get(timeout=timeout);r.update({'input':line,'latency':time.monotonic()-start});return r
 def close(self):
  self.send('/quit');self.process.stdin.close();self.process.wait(timeout=4);self.reader.join(3);self.raw.close();self.err.write(self.process.stderr.read());self.err.close()
JS=r'''
const b=Process.getModuleByName('hoi4.exe').base;let last=0,intervals=[],spans=[],calls=0;
Interceptor.attach(b.add(0xdd3a50),{onEnter(){let now=Date.now();this.start=now;if(last)intervals.push(now-last);last=now;},onLeave(){spans.push(Date.now()-this.start);}});
Interceptor.attach(b.add(0x24b4d60),{onEnter(){calls++;}});
rpc.exports={sample(){let x={intervals,spans,calls};intervals=[];spans=[];return x;},camera(){let c=b.add(0x332f698).readPointer().add(0x750).readPointer();return c.add(0x69c).readFloat();}};
'''
def main():
 assert not (D/'soak_result.json').exists(),'preserve run'
 pid=V.pid();fixture=D/'logs';fixture.mkdir(exist_ok=True)
 for n in ['game','error','plugin']:(fixture/(n+'.log')).write_bytes(b'')
 for p in frida.get_local_device().enumerate_processes():
  if p.name.lower()=='hoi4_debug_console.exe':
   h=K.OpenProcess(0x100001,False,p.pid);K.TerminateProcess(h,0);K.WaitForSingleObject(h,3000);K.CloseHandle(h)
 sess=Session(pid,fixture);session=frida.attach(pid);sc=session.create_script(JS);sc.load()
 rows=[];commands=[];expected=collections.Counter();records=[];writes=0;fake=[];current='setup';terminated=None
 def check(name,ok,detail=None):
  rows.append({'name':name,'ok':bool(ok),'detail':detail});print(name,'PASS' if ok else 'FAIL',flush=True)
  if not ok and name in ['reserved-lane-while-four-normal-peers-occupied','local-input-responsive-during-blocked-game','pre-execution-cancel','cancel-not-late-executed']:raise RuntimeError('stop criterion: '+name)
 def command(line,expect=0):
  r=sess.command(line);commands.append(r)
  if r['status']!=expect or (expect==0 and r['ok']!=1):raise RuntimeError('unexpected command '+str(r))
  return r
 def occupy():
  for _ in range(4):
   h=K.CreateFileW(r'\\.\pipe\hoi4-plugin-debug-v1-'+str(pid),0xc0000000,0,None,3,0,None)
   if h!=V.INVALID:fake.append(h)
 def release():
  for h in fake:K.CloseHandle(h)
  fake.clear()
 handles={n:(fixture/(n+'.log')).open('ab',buffering=0) for n in ['game','error','plugin']}
 try:
  command('gamespeed 0');command('event zzdcstress.0');command('help setcamheight')
  occupy();r=command('help setcamheight');check('reserved-lane-while-four-normal-peers-occupied',r['latency']<3,r);release()
  tid=r['thread'];h=K.OpenThread(2,False,tid);K.SuspendThread(h)
  try:
   t=time.monotonic();sess.send('setcamheight 1234');sess.send('/help');assert sess.local.wait(1)
   check('local-input-responsive-during-blocked-game',time.monotonic()-t<1)
   result=sess.results.get(timeout=7);commands.append(dict(result,input='setcamheight 1234',latency=time.monotonic()-t));check('pre-execution-cancel',result['status']==2,result)
  finally:K.ResumeThread(h);K.CloseHandle(h)
  time.sleep(1);check('cancel-not-late-executed',abs(sc.exports_sync.camera()-1234)>.1)
  # Reference workload and instrumentation stay identical across phases.
  start=time.monotonic();next_sample=start;next_command=start;next_load=start;next_peers=start;end=start+2700
  samples=(D/'samples.jsonl').open('w',encoding='utf-8');live=(D/'progress.json')
  while time.monotonic()<end:
   now=time.monotonic();elapsed=now-start
   phase='baseline' if elapsed<300 else 'boundary' if elapsed<900 else 'combined' if elapsed<2100 else 'recovery'
   if phase!=current:
    release();current=phase;print('PHASE',phase,'elapsed',round(elapsed,2),flush=True)
   if phase=='boundary' and now>=next_peers:
    release();occupy();next_peers=now+5
   if phase=='combined' and now>=next_load:
    for src,file in handles.items():
     count=2000 if int(elapsed)%60<4 else 10
     text=''.join('SEQ:%08d source=%s 中文日志 payload\n'%(expected[src]+j,src) for j in range(count));file.write(text.encode());expected[src]+=count
    next_load=now+.25
   if now>=next_command:
    if phase=='combined' and int(elapsed)%17==0:
     r=command('event zzdcstress.1');writes+=1
    elif phase=='combined' and int(elapsed)%23==0:command('setcamheight '+str(500+(int(elapsed)%3)*50))
    else:command('help setcamheight')
    next_command=now+(.2 if phase in ['boundary','combined'] else 2)
   if now>=next_sample:
    metric={'elapsed':elapsed,'phase':phase,'game':resources(pid),'helper':resources(sess.process.pid),'frame':sc.exports_sync.sample(),'expected_logs':dict(expected),'observed_logs':dict(sess.log_counts)}
    if metric['game'] is None or metric['helper'] is None:raise RuntimeError('process resource sampling unavailable')
    records.append(metric);samples.write(json.dumps(metric,ensure_ascii=False)+'\n');samples.flush()
    for role in ['game','helper']:
     if records and metric[role]['private']-records[0][role]['private']>2*1024**3:raise RuntimeError(role+' growth exceeded 2GiB stop threshold')
    live.write_text(json.dumps({'pid':pid,'helper_pid':sess.process.pid,'phase':phase,'elapsed':elapsed,'commands':len(commands),'writes':writes,'expected_logs':dict(expected),'observed_logs':dict(sess.log_counts)},ensure_ascii=False,indent=2),encoding='utf-8')
    next_sample=now+1
   if sess.line_errors:raise RuntimeError('log sequence integrity '+str(sess.line_errors[:3]))
   time.sleep(.015)
  release();samples.close()
  command('event zzdcstress.2');command('setcamheight 500');time.sleep(1)
  game_log=pathlib.Path('C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log').read_text(encoding='utf-8',errors='replace')
  found=re.findall(r'DCSTRESS FINAL=([0-9.]+)',game_log);check('write-count-exact',bool(found) and float(found[-1])==writes,{'expected':writes,'actual':found[-1] if found else None})
  check('all-source-sequences-complete',all(sess.log_counts[n.upper()]==v for n,v in expected.items()) and not sess.line_errors,{'expected':dict(expected),'actual':dict(sess.log_counts)})
  phases={}
  for phase in ['baseline','boundary','combined','recovery']:
   subset=[x for x in records if x['phase']==phase];ints=[v for x in subset for v in x['frame']['intervals']];spans=[v for x in subset for v in x['frame']['spans']]
   phases[phase]={'samples':len(subset),'frame_interval_p95_ms':percentile(ints,.95),'update_span_p95_ms':percentile(spans,.95),'resources_start':{n:subset[0][n] for n in ['game','helper']},'resources_end':{n:subset[-1][n] for n in ['game','helper']}}
  light=[r['latency'] for r in commands if r['input']=='help setcamheight'];check('light-command-p95-under-one-second',percentile(light,.95)<=1,{'p95':percentile(light,.95),'max':max(light),'count':len(light)})
  base=phases['baseline']['frame_interval_p95_ms'];load=phases['combined']['frame_interval_p95_ms'];check('update-cadence-review-line',load<=base*1.1,{'baseline':base,'combined':load,'metric':'main-update cadence proxy, not GPU Present'})
  for role in ['game','helper']:
   change=phases['recovery']['resources_end'][role]['handles']-phases['baseline']['resources_start'][role]['handles'];check(role+'-handle-recovery',change<=4,{'delta':change})
  result={'completed_seconds':time.monotonic()-start,'rows':rows,'phases':phases,'commands':commands,'expected_logs':dict(expected),'observed_logs':dict(sess.log_counts),'line_errors':sess.line_errors,'writes':writes,'dll_sha256':hashlib.sha256((ROOT.parent/'hoi4_mod_plugin.dll').read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256((ROOT.parent/'hoi4_debug_console.exe').read_bytes()).hexdigest(),'gui_visual_tested':False,'multiplayer_live_tested':False,'gpu_present_measured':False,'passed':sum(r['ok'] for r in rows),'checks':len(rows)}
 except Exception as exc:
  terminated=repr(exc);result={'error':terminated,'rows':rows,'commands':commands,'elapsed':time.monotonic()-start if 'start' in locals() else None,'expected_logs':dict(expected),'observed_logs':dict(sess.log_counts),'line_errors':sess.line_errors}
 finally:
  release()
  for f in handles.values():f.close()
  try:sess.close()
  except Exception as exc:result['shutdown_error']=repr(exc)
  session.detach()
 result['exit']=int(bool(terminated) or any(not r['ok'] for r in rows) or 'shutdown_error' in result)
 (D/'soak_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('SOAK_RESULT',result['exit'],result.get('completed_seconds',result.get('elapsed')),flush=True);return result['exit']
if __name__=='__main__':raise SystemExit(main())
