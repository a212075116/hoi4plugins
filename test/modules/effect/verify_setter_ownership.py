import argparse,json,pathlib,re,sys,time
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/lib'));sys.path.insert(0,str(ROOT/'test/tools'))
import frida_host as FH
import hoi4_launch as HL
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def fixtures():
 expected=[];reload_expected=[]
 body=['add_namespace = zzsetterown','country_event = { id = zzsetterown.1 hidden = yes is_triggered_only = yes immediate = {']
 read=['country_event = { id = zzsetterown.2 hidden = yes is_triggered_only = yes immediate = {']
 def set_(lines,name,value,wide):lines.append(('set_variable64' if wide else 'set_variable')+' = { var = '+name+' value = '+value+' }')
 def check(lines,key,name,value,wide,table):
  table.append({'key':key,'value':value,'wide':wide})
  lines.extend(['set_variable = { sw_ok = 0 }','if = { limit = { plugin_check_variable64 = { var = '+name+' value = '+value+' compare = equals } } set_variable = { sw_ok = 1 } }',
               'log = "SLW '+key+' value=[?'+name+'] ok=[?sw_ok]"'])
 for label,scope,prefix in [('country','',''),('other','ARI',''),('state','335',''),('character','ABY_Hoshino',''),('global','','global.')]:
  if scope:body.append(scope+' = {');read.append(scope+' = {')
  n=prefix+'sw_same'
  for key,value,wide in [('first64','12345678901.125',True),('demote','2.5',False),('native_repeat','-3.5',False),('promote','-12345678901.125',True),('wide_repeat','5000000000.25',True)]:
   set_(body,n,value,wide);check(body,label+'.'+key,n,value,wide,expected)
  body.append('add_to_variable = { var = '+n+' value = 0.125 }');check(body,label+'.wide_add',n,'5000000000.375',True,expected)
  set_(body,n,'2.5',False);body.append('add_to_variable = { var = '+n+' value = 0.25 }');check(body,label+'.native_add',n,'2.75',False,expected)
  for i in range(32):
   set_(body,n,'5000000000.125',True);set_(body,n,'-1.5',False)
  check(body,label+'.churn_native',n,'-1.5',False,expected)
  set_(body,prefix+'sw_wide','12345678901.125',True)
  check(body,label+'.save_wide',prefix+'sw_wide','12345678901.125',True,expected)
  check(read,label+'.reload_native',n,'-1.5',False,reload_expected)
  check(read,label+'.reload_wide',prefix+'sw_wide','12345678901.125',True,reload_expected)
  if scope:body.append('}');read.append('}')
 # Exercise reset of process-local overflow debt, not merely three-slot identity.
 set_(body,'sw_operand','5000000000.125',True)
 set_(body,'sw_debt_plain','10',False);body.append('add_to_variable = { var = sw_debt_plain value = sw_operand }')
 set_(body,'sw_debt_plain','2.5',False);body.append('add_to_variable = { var = sw_debt_plain value = 0.25 }')
 check(body,'debt.native_reset','sw_debt_plain','2.75',False,expected)
 set_(body,'sw_debt_promote','10',False);body.append('add_to_variable = { var = sw_debt_promote value = sw_operand }')
 set_(body,'sw_debt_promote','12345678901.125',True);set_(body,'sw_debt_promote','3.5',False)
 body.append('add_to_variable = { var = sw_debt_promote value = 0.25 }');check(body,'debt.promote_then_native','sw_debt_promote','3.75',False,expected)
 body+=['set_variable = { sw_marker = 20261012 }','log = "SLW WRITE DONE"','} option = { name = zzsetterown.1.a } }']
 read+=['log = "SLW marker=[?sw_marker]"','log = "SLW RELOAD DONE"','} option = { name = zzsetterown.2.a } }']
 return '\n'.join(body+read)+'\n',expected,reload_expected
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+r'''
const base=Process.getModuleByName('hoi4.exe').base;const samples=[];const seen=new Set();
const container=new NativeFunction(base.add(0x542500),'pointer',['pointer','pointer','pointer','pointer','pointer','pointer','pointer','pointer','pointer','pointer']);
function lookup(c,name){if(c.isNull())return null;const table=c.add(24).readPointer(),mask=c.add(36).readU32();if(table.isNull()||mask>1048575)return null;
 let hash=2166136261;for(let ch of name)hash=Math.imul(hash^ch.charCodeAt(0),16777619)>>>0;const bucket=table.add((hash&mask)*48);
 for(let guard=0;guard<255;guard++){const p=bucket.add(guard*48),dist=p.add(4).readU8();if(dist<=guard)return null;
  if(p.readU32()===hash){const len=p.add(24).readU64().toNumber(),cap=p.add(32).readU64().toNumber();const s=(cap<=15?p.add(8):p.add(8).readPointer()).readUtf8String(len);if(s===name)return p.add(40).readS64().toString();}
 }return null;
}
function snapshot(self,ctx){if(seen.has(self.toString()))return;seen.add(self.toString());try{
 const d=self.add(88),n=d.add(112),size=n.add(16).readU64().toNumber(),cap=n.add(24).readU64().toNumber();const name=(cap<=15?n:n.readPointer()).readUtf8String(size);
 if(!name.startsWith('sw_'))return;const extra=Array.from({length:8},()=>Memory.alloc(8));const c=container(d,ctx,...extra);
 const lo=lookup(c,name),hi=lookup(c,name+'_var64h'),fr=lookup(c,name+'_var64f');let wide=false;
 if(lo!==null&&hi!==null&&fr!==null){const l=Number(lo),h=Number(hi),f=Number(fr);wide=l%100000===0&&h%100000===0&&f>0&&f<200000*100000&&f%100000===0;}
 samples.push({name,container:c.toString(),lo,hi,fr,wide});
}catch(e){samples.push({error:String(e)});}}
rpc.exports.samples=function(){return samples;};
'''
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def ready(reload=False):
 marker='End RestoreDeviceObjects' if reload else 'Launching SINGLEPLAYER-game';end=time.time()+240
 while marker not in read(DOC/'logs/game.log'):
  if time.time()>end or not HL.proc_alive():raise RuntimeError('game readiness')
  time.sleep(.5)
 time.sleep(32)
def execute(out,event,label,save=False):
 import frida
 addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',read(pathlib.Path(HL.LOG)))[-1]
 s=frida.attach(FH.find_pid());sc=s.create_script(js+"\nInterceptor.attach(ptr('0x"+addr+"'),{onEnter(a){snapshot(a[0],a[1]);}});");sc.load();commands=[]
 try:
  r=sc.exports_sync.exec('event',[event]);print(r,flush=True);commands.append({'input':event,'stdout':r});assert 'out->ok     = 1' in r;time.sleep(1)
  (out/(label+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
  if save:
   start=time.time();r=sc.exports_sync.exec('savegame',['swmode']);print(r,flush=True);commands.append({'input':'savegame swmode','stdout':r});assert 'out->ok     = 1' in r
   p=DOC/'save games/swmode.hoi4';end=time.time()+30
   while not p.exists() or p.stat().st_mtime<start:
    if time.time()>end:raise RuntimeError('fresh save')
    time.sleep(.2)
   (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
 finally:FH.detach(s)
 (out/(label+'_commands.json')).write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
 for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if p.exists():(out/(label+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
 tables=json.loads(read(out/'expected.json'));rows=[]
 for phase,expected in tables.items():
  if not (out/(phase+'_game.log')).exists():continue
  g=read(out/(phase+'_game.log'));found={k:(v,ok) for k,v,ok in re.findall(r'SLW (\S+) value=(\S+) ok=(\S+)',g)};samples=json.loads(read(out/(phase+'_samples.json')))
  for i,w in enumerate(expected):
   val,ok=found.get(w['key'],(None,None));sample=samples[i] if i<len(samples) else {};good=val is not None and Decimal(val)==Decimal(w['value']) and ok=='1' and sample.get('wide')==w['wide']
   if not w['wide']:good=good and (sample.get('fr') is None or sample.get('fr')=='0') and (sample.get('hi') is None or sample.get('hi')=='0')
   rows.append({**w,'observed':val,'condition':ok,'snapshot':sample,'ok':good})
 errors=[l for label in tables for l in read(out/(label+'_error.log')).splitlines() if 'zz_setter_ownership' in l]
 result={'checks':len(rows),'passed':sum(r['ok'] for r in rows),'failed':[r for r in rows if not r['ok']],'rows':rows,'errors':errors,'alive':HL.proc_alive()}
 if (out/'reload_game.log').exists():result['marker_ok']='SLW marker=20261012' in read(out/'reload_game.log')
 result['exit']=int(bool(result['failed']) or bool(errors) or not result['alive'] or result.get('marker_ok') is False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','failed']},indent=2));print('FAILED',json.dumps(result['failed'],indent=2));return result['exit']
def main():
 a=argparse.ArgumentParser();a.add_argument('phase');a.add_argument('--deploy',action='store_true');a.add_argument('--lifecycle',action='store_true');a.add_argument('--verify-only',action='store_true');a.add_argument('--attach',action='store_true');p=a.parse_args()
 out=ROOT/'test/reports/20261012_variable64_transaction/setter'/p.phase;out.mkdir(parents=True,exist_ok=True)
 if p.verify_only:return verify(out)
 if (out/'write_game.log').exists():raise RuntimeError('preserve phase')
 text,w,r=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps({'write':w,'reload':r},indent=2),encoding='utf-8');(DOC/'mod/bakaifa/events/zz_setter_ownership.txt').write_text(text,encoding='utf-8')
 if p.deploy:print('DEPLOY',HL.deploy(),flush=True)
 if not p.attach:HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready()
 execute(out,'zzsetterown.1','write',p.lifecycle)
 if p.lifecycle:HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True);execute(out,'zzsetterown.2','reload')
 return verify(out)
if __name__=='__main__':raise SystemExit(main())
