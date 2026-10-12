import pathlib,json,sys,time,re,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'test/lib'),str(ROOT/'test/tools'),str(ROOT/'test/modules/effect')]
import frida,frida_host as FH,hoi4_launch as HL
from verify_array_native_lifecycle import DOC,ready
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
out=ROOT/'test/reports/20261012_variable64_transaction/camera_unify'/sys.argv[1]
if out.exists():raise RuntimeError('preserve phase')
out.mkdir(parents=True)
text='add_namespace = zzc\n'
for i,body in [(1,'set_camera_height = 950.25'),(2,'add_camera_height = 49.75'),(3,'set_camera_height_lowerlimit = 100'),(4,'set_camera_height_upperlimit = 2500')]:
 text+='country_event = { id = zzc.'+str(i)+' hidden = yes is_triggered_only = yes immediate = { '+body+' log = "CAMSHARED '+str(i)+' DONE" } option = { name = zzc.a } }\n'
(out/'events.txt').write_text(text,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_camera_shared.txt').write_text(text,encoding='utf-8')
loc=DOC/'mod/bakaifa/localisation';loc.mkdir(exist_ok=True)
for lang in ['english','simp_chinese']:
 labels=['EFFECT_SET_CAMERA_HEIGHT','EFFECT_ADD_CAMERA_HEIGHT','EFFECT_SET_CAMERA_HEIGHT_LOWERLIMIT','EFFECT_SET_CAMERA_HEIGHT_UPPERLIMIT']
 (loc/('camera_shared_l_'+lang+'.yml')).write_text('l_'+lang+':\n'+''.join(' '+key+':0 "Camera test: $VAL$"\n' for key in labels),encoding='utf-8-sig')
print('DEPLOY',HL.deploy(),flush=True);HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True)
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+r'''
const base=Process.getModuleByName('hoi4.exe').base,plugin=Process.getModuleByName('hoi4_mod_plugin.dll'),legacy=[];
Interceptor.attach(base.add(0x12643F0),{onEnter(a){const p=this.returnAddress;if(p.compare(plugin.base)>=0&&p.compare(plugin.base.add(plugin.size))<0)legacy.push(p.toString());}});
rpc.exports.snapshot=function(){const obj=base.add(0x332F698).readPointer(),c=obj.add(0x750).readPointer();return {camera:c.toString(),height:c.add(0x69C).readFloat(),displayHeight:c.add(0x678).readFloat(),lower:c.add(0x6D0).readS32(),upper:c.add(0x6D4).readS32(),legacyCalls:legacy.length};};
'''
session=frida.attach(FH.find_pid());sc=session.create_script(js);commands=[];rows=[];original=None
def command(name,args):
 x=sc.exports_sync.exec(name,args);commands.append({'input':name+' '+' '.join(args),'stdout':x});assert 'out->ok     = 1' in x,x
def settled(key,value):
 end=time.monotonic()+6
 while True:
  x=sc.exports_sync.snapshot()
  if abs(x[key]-value)<.01:
   time.sleep(.4)
   x=sc.exports_sync.snapshot()
   if abs(x[key]-value)<.01:return x
  if time.monotonic()>end:raise RuntimeError('not settled '+key+' '+str(x))
  time.sleep(.05)
try:
 sc.load();original=sc.exports_sync.snapshot();(out/'original.json').write_text(json.dumps(original,indent=2),encoding='utf-8')
 command('setcamheight',['950.25']);reference=settled('height',950.25)
 command('setcamheight',['500']);settled('height',500)
 command('event',['zzc.1']);effect=settled('height',950.25);rows.append({'key':'set_equals_console','ok':effect['height']==reference['height'],'sample':effect})
 command('setcamheight',['500']);settled('height',500);command('event',['zzc.2']);effect=settled('height',549.75);rows.append({'key':'add_uses_shared_height','ok':abs(effect['height']-549.75)<.01,'sample':effect})
 rows.append({'key':'height_preserves_limits','ok':effect['lower']==original['lower'] and effect['upper']==original['upper']})
 command('event',['zzc.3']);effect=settled('lower',100);rows.append({'key':'lower_shared','ok':effect['lower']==100})
 command('setcameraheight_lowerlimit',[str(original['lower'])]);settled('lower',original['lower']);command('event',['zzc.3']);effect=settled('lower',100);rows.append({'key':'lower_repeated_input_preserved','ok':effect['lower']==100})
 command('event',['zzc.4']);effect=settled('upper',2500);rows.append({'key':'upper_shared','ok':effect['upper']==2500})
 command('setcameraheight_upperlimit',[str(original['upper'])]);settled('upper',original['upper']);command('event',['zzc.4']);effect=settled('upper',2500);rows.append({'key':'upper_repeated_input_preserved','ok':effect['upper']==2500})
 rows.append({'key':'no_legacy_rva_called_by_plugin','ok':effect['legacyCalls']==0,'calls':effect['legacyCalls']})
finally:
 (out/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
 time.sleep(.5)
 if original:
  command('setcameraheight_lowerlimit',[str(original['lower'])]);settled('lower',original['lower']);command('setcameraheight_upperlimit',[str(original['upper'])]);settled('upper',original['upper']);command('setcamheight',[str(original['height'])]);settled('height',original['height'])
 FH.detach(session)
for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
 if p.exists():(out/(n+'.log')).write_bytes(p.read_bytes())
errors=[l for l in (out/'error.log').read_text(encoding='utf-8',errors='replace').splitlines() if 'zz_camera_shared' in l]
rows.append({'key':'fixture_errors','ok':not errors})
r={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'alive':HL.proc_alive(),'dll_sha256':hashlib.sha256((ROOT.parent/'hoi4_mod_plugin.dll').read_bytes()).hexdigest(),'visual_verified':False};r['exit']=int(r['checks']!=r['passed'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');(out/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(r['exit'])
