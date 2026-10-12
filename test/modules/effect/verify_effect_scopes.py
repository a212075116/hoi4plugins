import argparse,json,pathlib,re,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/tools'));sys.path.insert(0,str(ROOT/'test/lib'))
import hoi4_launch as HL
import frida_host as FH
from decimal import Decimal
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def fixture():
 lines=['add_namespace = zzscopecheck','country_event = { id = zzscopecheck.1 hidden = yes is_triggered_only = yes immediate = {']
 for label,block in [('country',''),('other_country','ARI'),('state','335'),('character','ABY_Hoshino')]:
  if block:lines.append(block+' = {')
  lines += ['log = "SCS BEGIN '+label+'"','set_variable = { sc_native = 10.5 }',
            'set_variable64 = { var = sc_value value = 12345.125 }','add_to_variable = { var = sc_value value = 0.25 }',
            'log = "SCS '+label+' native=[?sc_native] value=[?sc_value]"',
            'add_time_for_hours = 0','add_camera_height = 0','log = "SCS END '+label+'"']
  if block:lines.append('}')
 lines += ['set_variable64 = { var = global.sc_global value = 10000000000.125 }',
           'add_to_variable = { var = global.sc_global value = 0.25 }','log = "SCS global value=[?global.sc_global]"',
           'set_variable64 = { var = sc_operand value = 2.5 }','set_variable64 = { var = sc_dest value = 5 }',
           'set_variable64 = { var = sc_limit value = 2.5 }','set_variable64 = { var = sc_ceiling value = 7.75 }',
           'set_variable64 = { var = global.sc_factor value = 1.25 }','set_variable64 = { var = sc_from_factor value = 4.5 }',
           'ARI = { set_variable = { sc_operand = 9.5 } set_variable64 = { var = sc_target value = 10 }',
           'multiply_variable = { var = sc_target value = ROOT.sc_operand }','log = "SCS root_operand value=[?sc_target]"',
           'clamp_variable = { var = sc_target min = ROOT.sc_limit max = ROOT.sc_ceiling }','log = "SCS root_clamp value=[?sc_target]"',
           'set_variable64 = { var = sc_prev value = 10 }','multiply_variable = { var = sc_prev value = PREV.sc_operand }','log = "SCS prev_operand value=[?sc_prev]"',
           'set_variable64 = { var = sc_gop value = 10 }','multiply_variable = { var = sc_gop value = global.sc_factor }','log = "SCS global_operand value=[?sc_gop]"',
           'add_to_variable = { var = ROOT.sc_dest value = 0.125 }','}',
           'log = "SCS root_destination value=[?sc_dest]"',
           'log = "SCS country_after value=[?sc_value]"',
           'ARI = { country_event = { id = zzscopecheck.2 } }',
           'log = "SCS DONE"','} option = { name = zzscopecheck.1.a } }',
           'country_event = { id = zzscopecheck.2 hidden = yes is_triggered_only = yes immediate = {',
           'set_variable64 = { var = sc_from value = 10 }','multiply_variable = { var = sc_from value = FROM.sc_from_factor }',
           'log = "SCS from_operand value=[?sc_from]"','log = "SCS CHILD DONE"','} option = { name = zzscopecheck.2.a } }']
 return '\n'.join(lines)+'\n'

probe=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+r'''
const samples=[];
const image=Process.getModuleByName('hoi4.exe').base;
const plugin=Process.getModuleByName('hoi4_mod_plugin.dll');
const provided=new NativeFunction(image.add(0x537d90),'int',['pointer']);
Interceptor.attach(image.add(0x53d9e0),{onEnter(args){
 try{
  const self=args[0],ctx=args[1],vt=self.readPointer(),execute=vt.add(104).readPointer();
  const custom=execute.compare(plugin.base)>=0&&execute.compare(plugin.base.add(plugin.size))<0;
  const variable=vt.equals(image.add(0x2775698))&&self.add(505).readU32()===0x53343656;
  if((!custom&&!variable)||samples.length>=40)return;
  const mask=new NativeFunction(vt.add(152).readPointer(),'int',['pointer'])(self);
  samples.push({kind:variable?'variable64':'global_custom',self:self.toString(),context:ctx.toString(),supported:mask,provided:provided(ctx),country:ctx.add(8).readS32(),state:ctx.add(168).readS32()});
 }catch(e){samples.push({error:String(e)});}
}});
rpc.exports.scopeSamples=function(){return samples;};
'''
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''

def verify(out):
 report=json.loads(read(out/'report.json'));g='\n'.join(report['lines'])
 expected={**{k:'12345.375' for k in ['country','other_country','state','character','country_after']},
           'global':'10000000000.375','root_operand':'25','root_clamp':'7.75','prev_operand':'25',
           'global_operand':'12.5','root_destination':'5.125','from_operand':'45'}
 observed=dict(re.findall(r'SCS (\w+) (?:native=\S+ )?value=(\S+)',g))
 rows=[{'key':k,'expected':v,'observed':observed.get(k),'ok':k in observed and Decimal(observed[k])==Decimal(v)} for k,v in expected.items()]
 customs=[s for s in report['samples'] if s.get('kind')=='global_custom']
 ok=all(r['ok'] for r in rows) and not report['errors'] and report['alive'] and len(customs)==8 and all(s['supported']==0 for s in customs) and {s['provided'] for s in customs}=={2,4,8}
 result={'passed':sum(r['ok'] for r in rows),'checks':len(rows),'rows':rows,'global_callbacks':len(customs),'scope_masks_ok':ok,'exit':0 if ok else 1}
 (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return result['exit']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--attach',action='store_true');ap.add_argument('--verify-only',action='store_true');args=ap.parse_args()
 out=ROOT/'test/reports/20261012_variable64_transaction/scope'/args.phase;out.mkdir(parents=True,exist_ok=True)
 if args.verify_only:return verify(out)
 if (out/'game.log').exists():raise RuntimeError('preserve prior phase')
 if not args.attach:
  body=fixture();(out/'events.txt').write_text(body,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_effect_scope_check.txt').write_text(body,encoding='utf-8')
  HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
  deadline=time.time()+240
  while 'Launching SINGLEPLAYER-game' not in read(DOC/'logs/game.log'):
   if not HL.proc_alive():raise RuntimeError('game died')
   if time.time()>deadline:raise TimeoutError('in-game')
   time.sleep(.5)
  time.sleep(32)
 import frida
 session=frida.attach(FH.find_pid());sc=session.create_script(probe);sc.load()
 try:
  result=sc.exports_sync.exec('event',['zzscopecheck.1']);print(result,flush=True)
  if 'out->ok     = 1' not in result:raise RuntimeError(result)
  deadline=time.time()+20
  while 'SCS DONE' not in read(DOC/'logs/game.log') and time.time()<deadline:time.sleep(.2)
  if 'zzscopecheck.2' in read(out/'events.txt'):
   deadline=time.time()+15
   while 'SCS CHILD DONE' not in read(DOC/'logs/game.log') and time.time()<deadline:time.sleep(.2)
  samples=sc.exports_sync.scopeSamples();(out/'samples.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
 finally:FH.detach(session)
 for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if p.exists():(out/(n+'.log')).write_bytes(p.read_bytes())
 g=read(out/'game.log');e=read(out/'error.log')
 lines=[l for l in g.splitlines() if 'SCS ' in l]
 errors=[l for l in e.splitlines() if 'zz_effect_scope_check' in l or 'Invalid Scope' in l]
 report={'lines':lines,'errors':errors,'samples':samples,'alive':HL.proc_alive()};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
 return verify(out)
if __name__=='__main__':raise SystemExit(main())
