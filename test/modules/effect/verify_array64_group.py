import argparse, hashlib, json, pathlib, re, sys, time
from decimal import Decimal
import verify_array_readonly as R
ROOT=R.ROOT;TX=ROOT/'test/reports/20261012_variable64_transaction';SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_group_readonly.c'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "native_array_readonly.c"',R.SOURCE.read_text(encoding='utf-8'))
def split(raw):
    lo=raw&0xffffffff;hi=(raw>>32)&0xffffffff
    lo=lo-(1<<32) if lo>=(1<<31) else lo;hi=hi-(1<<32) if hi>=(1<<31) else hi
    flags=(1 if lo==-(1<<31) else 0)|(2 if hi==-(1<<31) else 0)
    return [0 if flags&1 else lo,0 if flags&2 else hi,1+flags]
def fixtures():
    expected=[];write=['add_namespace = zzarraygroup','country_event = { id = zzarraygroup.1 hidden = yes is_triggered_only = yes immediate = {'];reload=['country_event = { id = zzarraygroup.2 hidden = yes is_triggered_only = yes immediate = {']
    def group(label,name,scope='',prefix='',raws=None,variant='valid',status=1):
        if raws is None:raws=[1234567890112500,-9223372036854775808,9223372036854775807,-1,250000]
        root=prefix+'__v64a_'+name;columns=[split(v) if i!=4 else ['2.5',0,0] for i,v in enumerate(raws)]
        if variant=='kind':columns[-1][2]=5
        if variant=='fraction':columns[-1][0]='0.00001';columns[-1][2]=1
        if variant=='range':columns[-1][0]=2147483648;columns[-1][2]=1
        if variant=='nativehi':columns[-1][1]=1
        if scope:write.append(scope+' = {');reload.append(scope+' = {')
        if variant not in ['absent','orphan']:
            for suffix,value in [('_ver',1 if variant=='version' else 2),('_gen',3 if variant=='odd' else 2),('_len','1.5' if variant=='lenfraction' else len(raws))]:
                if variant=='manifest' and suffix=='_gen':continue
                write.append('set_variable = { '+root+suffix+' = '+str(value)+' }')
            for col,suffix in enumerate(['_lo','_hi','_kind']):
                write.append('clear_array = '+root+suffix)
                if not raws:write.append('set_variable = { '+root+suffix+'^num = 0 }')
                for index,triple in enumerate(columns):
                    if variant=='shape' and col==1 and index==len(columns)-1:continue
                    write.append('add_to_array = { array = '+root+suffix+' value = '+str(triple[col])+' }')
        if variant=='orphan':write.append('set_variable = { '+root+'_lo^4095 = 9 }')
        if variant=='extra':write.append('set_variable = { '+root+'_lo^9 = 9 }')
        if variant=='missing':write.append('clear_variable = '+root+'_hi^4')
        # The trigger is only a synchronous scope capture point, not a group read API.
        for lines in [write,reload]:lines.append('if = { limit = { plugin_check_variable64 = { var = '+prefix+'ag_'+name+' value = 0 compare = equals } } log = "AG '+label+' captured" }')
        expected.append({'label':label,'name':name,'status':status,'raws':[str(v) for v in raws] if status==1 else [],'scope':scope or prefix or 'country'})
        if scope:write.append('}');reload.append('}')
    for label,scope,prefix,raw in [('country','','',1234567890112500),('other','ARI','',-1234567890112500),('state','335','',712500),('character','ABY_Hoshino','',-250000),('global','','global.',612500)]:
        group(label,'shared',scope,prefix,[raw,-9223372036854775808,9223372036854775807,-1,250000])
    group('long','abcdefghijklmnopqrst')
    for name,variant,status in [('empty','valid',2),('absent','absent',0),('orphan','orphan',-3),('partial','manifest',-2),('version','version',-4),('odd','odd',-5),('length','lenfraction',-6),('shape','shape',-7),('badkind','kind',-8),('badfraction','fraction',-8),('badrange','range',-8),('nativehi','nativehi',-8),('extra','extra',-3),('missing','missing',-3)]:
        group(name,name,raws=[] if name=='empty' else None,variant=variant,status=status)
    # Similar logical names must not be mistaken for each other's reserved namespace.
    group('suffix_name','shared_lo',raws=[750000,-9223372036854775808,9223372036854775807,-1,250000])
    write+=['set_variable = { ag_marker = 20261012 }','log = "AG WRITE DONE"','} option = { name = zzarraygroup.1.a } }']
    reload+=['log = "AG marker=[?ag_marker]"','log = "AG RELOAD DONE"','} option = { name = zzarraygroup.2.a } }']
    return '\n'.join(write+reload)+'\n',expected
def probe(address):
    js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nconst source='+json.dumps(expanded())+';\n'+r'''
const base=Process.getModuleByName('hoi4.exe').base;
const copy=new NativeCallback((s,d,n)=>{try {if(n.toNumber()>4096)return 0;d.writeByteArray(s.readByteArray(n.toNumber()));return 1;}catch(e){return 0;}},'int',['pointer','pointer','uint64']);
const cm=new CModule(source,{na_read_memory:copy});
const readGroup=new NativeFunction(cm.Array64Group_Read,'int',['pointer','pointer','int','int','pointer','pointer','pointer']);
const resolve=new NativeFunction(base.add(0x542500),'pointer',Array(10).fill('pointer'));
const samples=[];
function text(p){const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();if(n>100)throw Error('name');return(cap<=15?p:p.readPointer()).readUtf8String(n);}
function bytes(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(v=>v.toString(16).padStart(2,'0')).join('');}
function snap(c){const mask=c.add(36).readU32(),spill=c.add(40).readU8();if(mask>1048575)throw Error('mask');return bytes(c,48)+bytes(c.add(24).readPointer(),48*(mask+1+spill));}
function one(c,name,index,gen=-1){const v=Memory.alloc(8),n=Memory.alloc(4),g=Memory.alloc(4);v.writeS64(123);n.writeS32(-99);g.writeS32(-99);const status=readGroup(c,Memory.allocUtf8String(name),index,gen,v,n,g);return{status,raw:v.readS64().toString(),count:n.readS32(),generation:g.readS32()};}
function capture(self,ctx){try{const d=self.add(88),n=text(d.add(112));if(!n.startsWith('ag_')||n==='ag_marker')return;const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),before=snap(c),first=one(c,name,0),values=[];
 if(first.status===1){for(let i=0;i<first.count;i++)values.push(one(c,name,i));}
 samples.push({name,container:c.toString(),first,values,stale:one(c,name,0,0),bounds:one(c,name,-1),noMutation:before===snap(c)});
}catch(e){samples.push({error:String(e)});}}
rpc.exports.samples=()=>samples;
''' + "\nInterceptor.attach(ptr('0x"+address+"'),{onEnter(a){capture(a[0],a[1]);}});"
    return js
def execute(out,phase,event,save=False):
    import frida
    address=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1]
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8')
    s=frida.attach(R.FH.find_pid());sc=s.create_script(probe(address));commands=[]
    try:
        sc.load();x=sc.exports_sync.exec('event',[event]);print(x,flush=True);commands.append({'input':'event '+event,'stdout':x});assert 'out->ok     = 1' in x
        (out/(phase+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
        if save:
            start=time.time();x=sc.exports_sync.exec('savegame',['aggroup']);print(x,flush=True);commands.append({'input':'savegame aggroup','stdout':x});assert 'out->ok     = 1' in x
            p=R.DOC/'save games/aggroup.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    expected=json.loads(R.read(out/'expected.json'));rows=[];ids={}
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'))
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()})
        rows.append({'key':phase+'.capture','ok':len(samples)>=len(expected) and not any('error' in s for s in samples),'count':len(samples)})
        ids[phase]=[s.get('container') for s in samples[:5]]
        rows.append({'key':phase+'.scopes','ok':len(set(ids[phase]))==5})
        for e,s in zip(expected,samples):
            f=s.get('first',{});ok=s.get('name')==e['name'] and f.get('status')==e['status'] and s.get('noMutation') and 'AG '+e['label']+' captured' in g
            if e['status']==1:ok=ok and [v['raw'] for v in s['values']]==e['raws'] and all(v['status']==1 and v['generation']==2 for v in s['values']) and s['stale']['status']==-9 and s['bounds']['status']==2
            elif e['status']==2:ok=ok and f['count']==0 and f['generation']==2 and f['raw']=='123'
            else:ok=ok and f.get('raw')=='123' and f.get('count')==-99 and f.get('generation')==-99
            rows.append({'key':phase+'.'+e['label'],'ok':bool(ok),'expected':e,'observed':s})
        originals={(s.get('container'),s.get('name')):s for s in samples[:len(expected)]}
        fields=['first','values','stale','bounds']
        rows.append({'key':phase+'.all_samples','ok':all(s.get('noMutation') and
            (s.get('container'),s.get('name')) in originals and all(s.get(f)==originals[(s.get('container'),s.get('name'))].get(f) for f in fields) for s in samples)})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_group' in l]
    rows.append({'key':'restart_marker','ok':'AG marker=20261012' in R.read(out/'reload_game.log')});rows.append({'key':'parser_errors','ok':not errors})
    r={'checks':len(rows),'passed':sum(v['ok'] for v in rows),'rows':rows,'errors':errors,'identities':ids,'alive':R.HL.proc_alive(),'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'write_api_enabled':False};r['exit']=int(r['checks']!=r['passed'] or not r['alive'])
    (out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILURES',json.dumps([v for v in rows if not v['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_group'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_group.txt').write_text(text,encoding='utf-8')
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write','zzarraygroup.1',True)
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload','zzarraygroup.2');return verify(out)
if __name__=='__main__':raise SystemExit(main())
