import json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'test/lib'),str(ROOT/'test/tools')]
import frida,frida_host as FH,hoi4_launch as HL
sys.stdout.reconfigure(encoding='utf-8',errors='replace');out=ROOT/'test/reports/20261012_variable64_transaction/api'/(sys.argv[1] if len(sys.argv)>1 else 'tooltips');out.mkdir(parents=True,exist_ok=True)
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
localization=DOC/'mod/bakaifa/localisation';localization.mkdir(exist_ok=True)
for lang in ['english','simp_chinese']:
    text='l_'+lang+':\n PLUGIN_CHECK_ARRAY64:0 "Array64 $LEFT$ $COMPARISON$ $RIGHT$ ($RESULT$)"\n'
    (localization/('array64_api_l_'+lang+'.yml')).write_text(text,encoding='utf-8-sig')
# Existing session needs a reload to load localization; source safety does not depend on localization being present.
log=pathlib.Path(HL.LOG).read_text(encoding='utf-8',errors='replace');addr=re.findall(r'\[trg\] \+ check_array64.*eval=([0-9A-Fa-f]+)',log)[-1]
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+r'''
const base=Process.getModuleByName('hoi4.exe').base,plugin=Process.getModuleByName('hoi4_mod_plugin.dll'),rows=[];
const release=new NativeFunction(base.add(0x21C9B00),'void',['pointer']);
function text(p){const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();return(cap<=15?p:p.readPointer()).readUtf8String(n);}
function readTip(self,ctx,invert){const out=Memory.alloc(32);out.writeByteArray(new Uint8Array(32));out.add(24).writeU64(15);
 const fn=new NativeFunction(self.readPointer().add(168).readPointer(),'pointer',['pointer','pointer','pointer','uint8','int']);fn(self,out,ctx,invert,0);const value=text(out);if(out.add(24).readU64().toNumber()>15)release(out.readPointer());return value;}
Interceptor.attach(base.add(0x53D9E0),{onEnter(a){try{const self=a[0],vt=self.readPointer(),exec=vt.add(104).readPointer();if(exec.compare(plugin.base)<0||exec.compare(plugin.base.add(plugin.size))>=0)return;
 const fn=new NativeFunction(vt.add(56).readPointer(),'pointer',['pointer','pointer','pointer']);const out=Memory.alloc(32);out.writeByteArray(new Uint8Array(32).fill(0xA5));fn(self,out,a[1]);const value=text(out);if(value.startsWith('Array64'))rows.push({kind:'effect',text:value});if(out.add(24).readU64().toNumber()>15)release(out.readPointer());
}catch(e){rows.push({error:String(e)});}}});
rpc.exports.samples=()=>rows;
''' + "\nInterceptor.attach(ptr('0x"+addr+"'),{onEnter(a){try{rows.push({kind:'trigger',normal:readTip(a[0],a[1],0),inverse:readTip(a[0],a[1],1)});}catch(e){rows.push({error:String(e)});}}});"
session=frida.attach(FH.find_pid());sc=session.create_script(js)
try:
    sc.load();x=sc.exports_sync.exec('event',['zzap64.1']);assert 'out->ok     = 1' in x;rows=sc.exports_sync.samples();(out/'command.txt').write_text(x,encoding='utf-8')
finally:FH.detach(session)
(out/'samples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
checks=[{'key':'no_errors','ok':not any('error' in r for r in rows)}, {'key':'effect_constructs_uninitialized_output','ok':any(r.get('kind')=='effect' and '12345678901.125' in r['text'] for r in rows)}, {'key':'triggers_called','ok':sum(r.get('kind')=='trigger' for r in rows)>=10},
 {'key':'full_precision_normal_inverse','ok':any(r.get('kind')=='trigger' and '12345678901.125 == 12345678901.125' in r['normal'] and '12345678901.125 != 12345678901.125' in r['inverse'] for r in rows)}]
r={'checks':len(checks),'passed':sum(v['ok'] for v in checks),'rows':checks,'visual_hover_verified':False,'localized_math_verified':checks[-1]['ok'],'localized_result_encoding_visual_verified':False};r['exit']=int(r['passed']!=r['checks']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(r['exit'])
