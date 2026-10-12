import argparse,hashlib,json,pathlib,re,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/lib'));sys.path.insert(0,str(ROOT/'test/tools'))
import frida_host as FH
import hoi4_launch as HL
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
tips=[('scalar','plugin_value_half > 0.49999','0.5','>','0.49999',True),
 ('equal','plugin_check_variable64 = { var = dt_big value = 12345678901.125 compare = equals }','12345678901.125','==','12345678901.125',True),
 ('false','plugin_check_variable64 = { var = dt_big value = 12345678901.12501 compare = greater_than }','12345678901.125','>','12345678901.12501',False),
 ('negative','plugin_check_variable64 = { var = dt_negative value = -0.00002 compare = greater_than }','-0.00001','>','-0.00002',True),
 ('root','ARI = { plugin_check_variable64 = { var = ROOT.dt_big value = ROOT.dt_big compare = equals } }','12345678901.125','==','12345678901.125',True),
 ('global','plugin_check_variable64 = { var = global.dt_global value = 2.5 compare = equals }','2.5','==','2.5',True),
 ('temp','plugin_check_variable64 = { var = dt_temp value = 2.5 compare = equals }','2.5','==','2.5',True),
 ('shadow','plugin_check_variable64 = { var = dt_shadow value = 2.5 compare = equals }','2.5','==','2.5',True),
 ('missing','plugin_check_variable64 = { var = dt_missing value = 0 compare = equals }','0','==','0',True),
 ('empty','plugin_check_variable64 = { }','?','>=','?',None)]
def fixture():
 lines=['add_namespace = zztooltiplife','country_event = { id = zztooltiplife.1 hidden = yes is_triggered_only = yes immediate = {',
 'set_variable64 = { var = dt_big value = 12345678901.125 }','set_variable64 = { var = dt_negative value = -0.00001 }',
 'set_variable64 = { var = global.dt_global value = 2.5 }','set_variable64 = { var = dt_shadow value = 12345678901.125 }',
 'set_variable = { dt_marker = 20261012 }','set_temp_variable = { dt_temp = 2.5 }','set_temp_variable = { dt_shadow = 2.5 }',
 'set_variable = { dt_dynamic = num_owned_states }','log = "DT dynamic=[?dt_dynamic]"']
 for tag,condition,*_ in tips:
  lines+=['set_variable = { dt_result = 0 }','if = { limit = { '+condition+' } set_variable = { dt_result = 1 } }','log = "DT_TIP_'+tag+'=[?dt_result]"']
 for tag,condition in [('native_temp','check_variable = { var = dt_temp value = 2.5 compare = equals }'),
                       ('native_shadow','check_variable = { var = dt_shadow value = 2.5 compare = equals }'),
                       ('native_missing','check_variable = { var = dt_missing value = 0 compare = equals }'),
                       ('dynamic','plugin_check_variable64 = { var = dt_dynamic value = num_owned_states compare = equals }'),
                       ('native_dynamic','check_variable = { var = dt_dynamic value = num_owned_states compare = equals }')]:
  lines+=['set_variable = { dt_result = 0 }','if = { limit = { '+condition+' } set_variable = { dt_result = 1 } }','log = "DT '+tag+'=[?dt_result]"']
 lines+=['log = "DT WRITE marker=[?dt_marker] big=[?dt_big] negative=[?dt_negative]"','log = "DT DONE"','} option = { name = zztooltiplife.1.a } }',
 'country_event = { id = zztooltiplife.2 hidden = yes is_triggered_only = yes immediate = {',
 'log = "DT READ marker=[?dt_marker] big=[?dt_big] negative=[?dt_negative] shadow=[?dt_shadow]"',
 'set_variable = { dt_result = 0 }','if = { limit = { plugin_check_variable64 = { var = dt_big value = 12345678901.125 compare = equals } } set_variable = { dt_result = 1 } }',
 'log = "DT_TIP_reload=[?dt_result]"','log = "DT RELOAD DONE"','} option = { name = zztooltiplife.2.a } }']
 return '\n'.join(lines)+'\n'
def localization():
 for lang in ['english','simp_chinese']:
  reference=ROOT/('test/modules/trigger/typed_tooltip_l_'+lang+'_reference.yml')
  content=reference.read_bytes();assert content.startswith(b'\xef\xbb\xbf')
  (DOC/('mod/bakaifa/localisation/zz_typed_tooltips_l_'+lang+'.yml')).write_bytes(content)
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nconst tipTags='+json.dumps([t[0] for t in tips])+';\n'+r'''
const base=Process.getModuleByName('hoi4.exe').base,plugin=Process.getModuleByName('hoi4_mod_plugin.dll');
let last=null,busy=false;const samples=[];const seen=new Set();const debug={wrapper:0,direct:0,lang:0,keys:[]};
const release=new NativeFunction(base.add(0x21c9b00),'void',['pointer']);
Interceptor.attach(base.add(0x54d0b0),{onEnter(args){debug.wrapper++;try{const fn=args[0].readPointer().add(176).readPointer();if(fn.compare(plugin.base)>=0&&fn.compare(plugin.base.add(plugin.size))<0)last=args[0];}catch(e){}}});
Interceptor.attach(base.add(0x12cf2b0),{onEnter(args){
 debug.lang++;const n=args[2].sub(args[1]).toInt32();if(n<0||n>160)return;const tag=args[1].readUtf8String(n);if(debug.keys.length<40)debug.keys.push(tag);
}});
function captureTip(self,context){
 if(busy||samples.length>=tipTags.length||seen.has(self.toString()))return;seen.add(self.toString());busy=true;
 try{const fn=new NativeFunction(self.readPointer().add(168).readPointer(),'pointer',['pointer','pointer','pointer','uchar','int']);
  const row={tag:tipTags[samples.length],self:self.toString(),context:context.toString(),mask:new NativeFunction(base.add(0x537d90),'uint',['pointer'])(context),flags:[]};
  const isBlock=self.readPointer().add(40).readPointer().equals(base.add(0x54fd00));
  for(const off of (isBlock?[88,296]:[96]))row.flags.push({offset:off,bytes:Array.from(new Uint8Array(self.add(off+8).readByteArray(8))),field100:self.add(off+100).readS32()});
  for(const inv of [0,1]){const out=Memory.alloc(32);fn(self,out,context,inv,0);const len=out.add(16).readU64().toNumber(),cap=out.add(24).readU64().toNumber();row[inv?'inverted':'normal']=(cap<=15?out:out.readPointer()).readUtf8String(len);if(cap>15)release(out.readPointer());}
  samples.push(row);
 }catch(e){samples.push({tag,error:String(e)});}finally{busy=false;}
}
rpc.exports.samples=function(){return samples;};
rpc.exports.debug=function(){return debug;};
'''
def capture(out,label):
 for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if p.exists():(out/(label+'_'+n+'.log')).write_bytes(p.read_bytes())
def ready(reload=False):
 deadline=time.time()+240;marker='End RestoreDeviceObjects' if reload else 'Launching SINGLEPLAYER-game'
 while marker not in read(DOC/'logs/game.log'):
  if time.time()>deadline or not HL.proc_alive():raise RuntimeError('game readiness')
  time.sleep(.5)
 time.sleep(32)
def execute(out,event,label,save=False):
 import frida
 log=read(pathlib.Path(HL.LOG));addresses=[]
 for name in ['plugin_value_half','plugin_check_variable64']:
  addresses.append(re.findall(r'\[trg\] \+ '+name+r'.*eval=([0-9A-Fa-f]+)',log)[-1])
 direct='\n'+''.join("Interceptor.attach(ptr('0x"+a+"'),{onEnter(args){debug.direct++;if(!busy){last=args[0];captureTip(args[0],args[1]);}}});" for a in addresses)
 session=frida.attach(FH.find_pid());sc=session.create_script(js+direct);sc.load();commands=[]
 try:
  r=sc.exports_sync.exec('event',[event]);commands.append({'input':event,'stdout':r});print(r,flush=True)
  if 'out->ok     = 1' not in r:raise RuntimeError(r)
  time.sleep(1);samples=sc.exports_sync.samples();(out/(label+'_debug.json')).write_text(json.dumps(sc.exports_sync.debug(),indent=2),encoding='utf-8')
  if save:
   start=time.time();r=sc.exports_sync.exec('savegame',['ttlife']);commands.append({'input':'savegame ttlife','stdout':r});print(r,flush=True)
   if 'out->ok     = 1' not in r:raise RuntimeError(r)
   p=DOC/'save games/ttlife.hoi4';deadline=time.time()+30
   while not p.exists() or p.stat().st_mtime<start:
    if time.time()>deadline:raise RuntimeError('fresh save missing')
    time.sleep(.2)
   (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
 finally:FH.detach(session)
 (out/(label+'_samples.json')).write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/(label+'_commands.json')).write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8');capture(out,label)
def verify(out):
 rows=[];samples=json.loads(read(out/'write_samples.json'));got={r.get('tag'):r for r in samples};g=read(out/'write_game.log')
 inverse={'>':'<=','<':'>=','==':'!=','!=':'==','<=':'>','>=':'<'}
 for tag,condition,left,op,right,result in tips:
  row=got.get(tag,{});label='Half' if tag=='scalar' else 'Variable64'
  for inv in [False,True]:
   o=inverse[op] if inv else op;r='§YUNAVAILABLE§!' if result is None else ('§GTRUE§!' if result!=inv else '§RFALSE§!')
   want=f'{label}: {left} {o} {right} ({r})\n';actual=row.get('inverted' if inv else 'normal')
   zh_result='§Y参数不可用§!' if result is None else ('§G满足§!' if result!=inv else '§R未满足§!')
   zh_label='半值比较' if tag=='scalar' else '64 位变量比较'
   zh_want=f'{zh_label}：{left} {o} {right}（{zh_result}）\n'
   rows.append({'key':tag+('_inverse' if inv else ''),'expected':want,'expected_chinese':zh_want,'observed':actual,'ok':actual is not None and actual.replace('\x11','§') in [want,zh_want]})
 errors=[l for l in read(out/'write_error.log').splitlines() if 'zz_tooltip_lifecycle' in l]
 boundary={key:(re.findall(r'DT '+key+r'=(\S+)',g) or [None])[-1] for key in ['dynamic','native_temp','native_shadow','native_missing','native_dynamic']}
 # Separate count capture from the dynamic boolean marker.
 count=(re.findall(r'DT dynamic=(\S+)',g) or [None])[0]
 boundary_ok=count is not None and float(count)>0 and all((re.findall(r'DT '+k+r'=(\S+)',g) or [None])[-1]=='1' for k in ['native_temp','native_shadow','native_missing','dynamic','native_dynamic'])
 boundary_ok=boundary_ok and all((re.findall(r'DT_TIP_'+tag+r'=(\S+)',g) or [None])[-1]==('1' if wanted else '0') for tag,_,_,_,_,wanted in tips)
 result={'checks':len(rows),'passed':sum(r['ok'] for r in rows),'rows':rows,'errors':errors,'boundary':boundary,'dynamic_count':count,'boundary_ok':boundary_ok,'alive':HL.proc_alive()}
 if (out/'reload_game.log').exists():
  rg=read(out/'reload_game.log');reload_samples=json.loads(read(out/'reload_samples.json'))
  wanted='DT READ marker=20261012 big=12345678901.125 negative=-0.00001 shadow=12345678901.125'
  expected_reload=['Variable64: 12345678901.125 == 12345678901.125 (§GTRUE§!)\n','64 位变量比较：12345678901.125 == 12345678901.125（§G满足§!）\n']
  result['reload_ok']=wanted in rg and any(r.get('normal','').replace('\x11','§') in expected_reload for r in reload_samples)
 result['exit']=int(result['passed']!=len(rows) or bool(errors) or not boundary_ok or not result['alive'] or result.get('reload_ok') is False)
 (out/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2));return result['exit']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--deploy',action='store_true');ap.add_argument('--lifecycle',action='store_true');ap.add_argument('--verify-only',action='store_true');ap.add_argument('--attach',action='store_true');a=ap.parse_args()
 out=ROOT/'test/reports/20261012_variable64_transaction/tooltip'/a.phase;out.mkdir(parents=True,exist_ok=True)
 if a.verify_only:return verify(out)
 if (out/'write_game.log').exists():raise RuntimeError('preserve phase')
 text=fixture();(out/'events.txt').write_text(text,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_tooltip_lifecycle.txt').write_text(text,encoding='utf-8');localization()
 if a.deploy:print('DEPLOY',HL.deploy(),flush=True)
 if not a.attach:
  HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready()
 execute(out,'zztooltiplife.1','write',a.lifecycle)
 if a.lifecycle:
  HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True);execute(out,'zztooltiplife.2','reload')
 return verify(out)
if __name__=='__main__':raise SystemExit(main())
