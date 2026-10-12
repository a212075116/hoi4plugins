import argparse,hashlib,json,pathlib,re,sys,time
import verify_array64_group as G
R=G.R;ROOT=G.ROOT;TX=G.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_existing_transaction.c'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
CASES=[{'name':'ok','stage':0,'rollback':0,'wide':1,'raw':'-9223372036854775808','want':1},
       {'name':'native','stage':0,'rollback':0,'wide':0,'raw':'250000','want':1}]
CASES += [{'name':'f'+str(i),'stage':i,'rollback':0,'wide':1,'raw':'9223372036854775807','want':2} for i in range(1,6)]
CASES += [{'name':'q'+str(i),'stage':5,'rollback':i,'wide':1,'raw':'9223372036854775807','want':-3} for i in range(1,5)]
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_group_readonly.c"',G.expanded())
def fixtures():
    write=['add_namespace = zzarraytx','country_event = { id = zzarraytx.1 hidden = yes is_triggered_only = yes immediate = {'];reload=['country_event = { id = zzarraytx.2 hidden = yes is_triggered_only = yes immediate = {'];expected=[]
    for label,scope,prefix in [('country','',''),('other','ARI',''),('state','335',''),('character','ABY_Hoshino',''),('global','','global.')]:
        if scope:write.append(scope+' = {');reload.append(scope+' = {')
        for case in CASES:
            name='tx'+case['name'];root=prefix+'__v64a_'+name
            write+=['set_variable64 = { var = '+prefix+name+' value = 12345678901.125 }','clear_array = '+prefix+name,
                'add_to_array = { array = '+prefix+name+' value = 2.5 }','add_to_array = { array = '+prefix+name+' value = 7.75 }']
            for suffix,v in [('ver',2),('gen',2),('len',2)]:write.append('set_variable = { '+root+'_'+suffix+' = '+str(v)+' }')
            triples=[G.split(1234567890112500),G.split(-1)]
            for col,suffix in enumerate(['lo','hi','kind']):
                write.append('clear_array = '+root+'_'+suffix)
                for triple in triples:write.append('add_to_array = { array = '+root+'_'+suffix+' value = '+str(triple[col])+' }')
            for lines,marker in [(write,'at_'),(reload,'ar_')]:
                lines+=['if = { limit = { plugin_check_variable64 = { var = '+prefix+marker+name+' value = 0 compare = equals } } log = "AT '+label+'.'+case['name']+' scalar=[?'+prefix+name+'] a0=[?'+prefix+name+'^0] a1=[?'+prefix+name+'^1]" }']
            expected.append({'label':label,**case,'group':name})
        if scope:write.append('}');reload.append('}')
    write+=['set_variable = { at_marker = 20261012 }','log = "AT WRITE DONE"','} option = { name = zzarraytx.1.a } }']
    reload+=['log = "AT marker=[?at_marker]"','log = "AT RELOAD DONE"','} option = { name = zzarraytx.2.a } }']
    return '\n'.join(write+reload)+'\n',expected
def probe(address):
    return (ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nconst source='+json.dumps(expanded())+';\nconst cases='+json.dumps(CASES)+';\n'+r'''
const base=Process.getModuleByName('hoi4.exe').base,rows=[],seen=new Set(),writes=[];
const nativeLookup=new NativeFunction(base.add(0xBC5C10),'pointer',['pointer','pointer','int64']);
function txt(p){const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();if(n>127)throw Error('name');return(cap<=15?p:p.readPointer()).readUtf8String(n);}
function slot(c,name){let h=2166136261;for(const ch of name)h=Math.imul(h^ch.charCodeAt(0),16777619)>>>0;const b=c.add(24).readPointer(),mask=c.add(36).readU32();if(mask>1048575)return null;
 for(let i=0;i<255;i++){const p=b.add(48*((h&mask)+i));if(p.add(4).readU8()<=i)return null;if(p.readU32()===h&&txt(p.add(8))===name)return p.add(40);}return null;}
const copy=new NativeCallback((s,d,n)=>{try{if(n.toNumber()>4096)return 0;d.writeByteArray(s.readByteArray(n.toNumber()));return 1;}catch(e){return 0;}},'int',['pointer','pointer','uint64']);
const writer=new NativeCallback((c,k,raw)=>{try{const name=k.readUtf8String(),existing=slot(c,name);if(!existing)return 0;
 const view=Memory.alloc(16);view.writePointer(k);view.add(8).writeU64(name.length);const p=nativeLookup(c,view,0);
 if(!p.equals(existing))throw Error('native slot mismatch');const before=p.readS64().toString();p.writeS64(raw);
 writes.push({container:c.toString(),key:name,before,after:p.readS64().toString()});return 1;
}catch(e){writes.push({error:String(e)});return 0;}},'int',['pointer','pointer','int64']);
const cm=new CModule(source,{na_read_memory:copy,tx_write_existing:writer});
const readGroup=new NativeFunction(cm.Array64Group_Read,'int',['pointer','pointer','int','int','pointer','pointer','pointer']);
const setGroup=new NativeFunction(cm.Array64_SetExisting,'int',['pointer','pointer','int','int','int64','int','int','int']);
const resolve=new NativeFunction(base.add(0x542500),'pointer',Array(10).fill('pointer'));
function bytes(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(v=>v.toString(16).padStart(2,'0')).join('');}
function snap(c){const mask=c.add(36).readU32(),spill=c.add(40).readU8();if(mask>1048575)throw Error('mask');return bytes(c,48)+bytes(c.add(24).readPointer(),48*(mask+1+spill));}
function protectedSnap(c,name){let value=snap(c);const table=c.add(24).readPointer();for(const suffix of ['gen','lo^0','hi^0','kind^0']){const p=slot(c,'__v64a_'+name+'_'+suffix);if(!p)throw Error('protected slot missing');const at=96+p.sub(table).toInt32()*2;value=value.slice(0,at)+'x'.repeat(16)+value.slice(at+16);}return value;}
function group(c,name){const v=Memory.alloc(8),n=Memory.alloc(4),g=Memory.alloc(4);v.writeS64(123);n.writeS32(-99);g.writeS32(-99);let status=readGroup(c,Memory.allocUtf8String(name),0,-1,v,n,g);const head={status,raw:v.readS64().toString(),count:n.readS32(),generation:g.readS32()},values=[];
 if(status===1)for(let i=0;i<head.count;i++){status=readGroup(c,Memory.allocUtf8String(name),i,-1,v,n,g);values.push({status,raw:v.readS64().toString()});}return {head,values};}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!n.startsWith('at_tx')&&!n.startsWith('ar_tx'))return;
 const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const params=cases.find(x=>name==='tx'+x.name);if(!params)throw Error('unknown case');const before=snap(c),protectedBefore=protectedSnap(c,name),baseline=group(c,name),start=writes.length;
 const result=n.startsWith('at_')?setGroup(c,Memory.allocUtf8String(name),0,2,new Int64(params.raw),params.wide,params.stage,params.rollback):null;
 const after=group(c,name),sameBytes=before===snap(c);const gen=slot(c,'__v64a_'+name+'_gen').readS64().toString();
 rows.push({name,container:c.toString(),result,baseline,after,gen,sameBytes,onlyExpectedSlotsChanged:protectedBefore===protectedSnap(c,name),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
rpc.exports.samples=()=>rows;
''' + "\nInterceptor.attach(ptr('0x"+address+"'),{onEnter(a){capture(a[0],a[1]);}});"
def execute(out,phase,event,save=False):
    import frida
    addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1]
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8');s=frida.attach(R.FH.find_pid());sc=s.create_script(probe(addr));commands=[]
    try:
        sc.load();x=sc.exports_sync.exec('event',[event]);print(x,flush=True);commands.append({'input':'event '+event,'stdout':x});assert 'out->ok     = 1' in x
        (out/(phase+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
        if save:
            start=time.time();x=sc.exports_sync.exec('savegame',['atx']);print(x,flush=True);commands.append({'input':'savegame atx','stdout':x});assert 'out->ok     = 1' in x
            p=R.DOC/'save games/atx.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    expected=json.loads(R.read(out/'expected.json'));rows=[];identities={}
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'))
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()})
        rows.append({'key':phase+'.captures','ok':len(samples)==len(expected) and not any('error' in s for s in samples),'count':len(samples)})
        identities[phase]=[s.get('container') for s in samples[::len(CASES)]]
        rows.append({'key':phase+'.scope_isolation','ok':len(set(identities[phase]))==5})
        for e,s in zip(expected,samples):
            a=s.get('after',{});head=a.get('head',{});good=s.get('name')==e['group'] and s.get('onlyExpectedSlotsChanged')
            if e['want']==1:good=good and head.get('status')==1 and head.get('generation')==4 and [v['raw'] for v in a['values']]==[e['raw'],'-1']
            elif e['want']==2:good=good and head.get('status')==1 and head.get('generation')==2 and [v['raw'] for v in a['values']]==['1234567890112500','-1']
            else:good=good and head.get('status')==-5 and head.get('raw')=='123' and s.get('gen')=='300000'
            if phase=='write':good=good and s.get('result')==e['want'] and (e['want']!=2 or s.get('sameBytes')) and not any('error' in w for w in s.get('writes',[]))
            else:good=good and s.get('sameBytes') and not s.get('writes')
            rows.append({'key':phase+'.'+e['label']+'.'+e['name']+'.transaction','ok':bool(good),'expected':e,'observed':s})
            match=re.findall(r'AT '+re.escape(e['label']+'.'+e['name'])+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g)
            rows.append({'key':phase+'.'+e['label']+'.'+e['name']+'.native_untouched','ok':bool(match) and match[-1]==('12345678901.125','2.5','7.75'),'observed':match})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_transaction' in l]
    rows += [{'key':'marker','ok':'AT marker=20261012' in R.read(out/'reload_game.log')},{'key':'parser_errors','ok':not errors}]
    r={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'identities':identities,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_write_api':False,'scope':'existing valid group; same length; one element; injected logical write/rollback failures'};r['exit']=int(r['checks']!=r['passed'] or not r['alive'])
    (out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([v for v in rows if not v['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');p.add_argument('--attach',action='store_true');a=p.parse_args();out=TX/'array_transaction'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_transaction.txt').write_text(text,encoding='utf-8')
    if not a.attach:R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready()
    execute(out,'write','zzarraytx.1',True)
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload','zzarraytx.2');return verify(out)
if __name__=='__main__':raise SystemExit(main())
