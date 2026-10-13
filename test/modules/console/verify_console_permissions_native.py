import frida,json,pathlib,subprocess,time
R=pathlib.Path(__file__).resolve().parents[3];D=R/'test/reports/20261012_variable64_transaction/console_permission'
p=next(x.pid for x in frida.get_local_device().enumerate_processes() if x.name.lower()=='hoi4.exe')
s=frida.attach(p)
js=r'''
const b=Process.getModuleByName('hoi4.exe').base,m=b.add(0x35e1a80).readPointer();
const orig=m.add(80).readPointer();let baseline=false,suppressIron=false,forceNetwork=false,count=0;
const networkPredicate=m.add(144).readPointer().readPointer().add(16).readPointer();
Interceptor.attach(networkPredicate,{onLeave(ret){if(forceNetwork)ret.replace(1);}});
Interceptor.attach(b.add(0x24b4d40),{onEnter(a){count++;this.manager=a[0];if(baseline){let permission=a[0].add(80).readPointer();if(suppressIron){this.iron=a[0].add(208).readPointer();a[0].add(208).writePointer(permission);}a[0].add(80).writePointer(orig);}},onLeave(){if(this.iron)this.manager.add(208).writePointer(this.iron);}});
rpc.exports={mode(old,iron,mp){baseline=old;suppressIron=old&&!iron&&!mp;forceNetwork=mp;},snapshot(){let state=b.add(0x332f260).readPointer();return {count,manager:m.toString(),original80:orig.toString(),current80:m.add(80).readPointer().toString(),current208:m.add(208).readPointer().toString(),uiState:m.add(216).readU16(),counter:m.add(220).readU32(),actualIronman:state.isNull()?null:!!(state.add(0xc0).readU8()&1)};}};
'''
sc=s.create_script(js);sc.load();rows=[];initial=sc.exports_sync.snapshot()
def command(line):
 c=[str(R.parent/'hoi4_debug_console.exe'),'--pid',str(p),'--command',line];q=subprocess.run(c,capture_output=True,timeout=15)
 return dict(command=c,stdout=q.stdout.decode('utf-8',errors='replace'),stderr=q.stderr.decode('utf-8',errors='replace'),exit=q.returncode)
try:
 for name,old,iron,mp,line in [('baseline_developer',True,False,False,'debug_dumpdiploactions'),('modified_developer',False,False,False,'debug_dumpdiploactions'),('baseline_ironman',True,True,False,'help setcamheight'),('modified_ironman',False,True,False,'help setcamheight'),('modified_multiplayer',False,False,True,'help setcamheight'),('modified_multiplayer_ironman',False,True,True,'help setcamheight')]:
  sc.exports_sync.mode(old,iron,mp);before=sc.exports_sync.snapshot();q=command(line);after=sc.exports_sync.snapshot()
  good=(q['exit']==3 and 'disabled in multiplayer' in q['stdout'] and after['count']==before['count']) if mp else (q['exit']==1 and ('ironman mode' in q['stdout'] if iron else 'only for developers' in q['stdout'])) if old else (q['exit']==0 and after['count']==before['count']+1)
  good=good and before['uiState']==after['uiState'] and before['current80']==after['current80'] and before['current208']==after['current208']
  rows.append(dict(name=name,ok=good,before=before,after=after,result=q));print(name,good,q['stdout'][:240],flush=True)
finally:
 sc.exports_sync.mode(False,False,False);final=sc.exports_sync.snapshot();sc.unload();s.detach()
x=dict(pid=p,rows=rows,passed=sum(r['ok'] for r in rows),checks=len(rows),initial=initial,final=final,actual_multiplayer=False,actual_ironman_save=initial['actualIronman'],scope='No-debug real Ironman session; network predicate return injected; old gates replayed only during synchronous native dispatch with selector restoration; no gamestate-bit or predicate-object-vtable mutation; native UI flags preserved')
x['exit']=int(x['passed']!=x['checks']);(D/'native.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(x,ensure_ascii=False,indent=2));raise SystemExit(x['exit'])
