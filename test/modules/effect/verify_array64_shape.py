import argparse,hashlib,inspect,json,pathlib,re,secrets,sys,time
import verify_array64_durable as D
import verify_array64_ownership as O
T=D.T;R=D.R;ROOT=D.ROOT;TX=D.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_shape_transaction.c'
CASES=['create','append','insert','erase','resizeup','resizedown','clear','rollback','quarantine','collision']
PARAMS={'create':[0,0,0,'-9223372036854775808',1,2,0,0], 'append':[1,0,2,'9223372036854775807',1,0,0,0],
 'insert':[2,1,2,'-9223372036854775808',1,0,0,0], 'erase':[3,0,2,'0',1,0,0,0],
 'resizeup':[5,0,2,'250000',0,4,0,0], 'resizedown':[5,0,2,'0',1,1,0,0],
 'clear':[4,0,2,'0',1,0,0,0], 'rollback':[2,1,2,'-9223372036854775808',1,0,14,0],
 'quarantine':[2,1,2,'-9223372036854775808',1,0,14,12], 'collision':[0,0,0,'0',1,2,0,0]}
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_ownership_gate.c"',O.expanded())
def fixtures():
    body=inspect.getsource(D.fixtures).replace('def fixtures():','def build():').replace("['persist','stale']",repr(CASES));ns=dict(vars(D));exec(body,ns);text,e=ns['build']();branch=[secrets.randbelow(2147483646)+1 for _ in range(4)]
    for row in e:row['stamps']=branch+[secrets.randbelow(2147483646)+1 for _ in range(4)]
    # The prepare event captures durable baselines; a separate event executes mutations.
    counters={};lines=[]
    for line in text.splitlines():
        m=re.search(r'var = (global\.)?(d[pqr])_(tx\w+)',line)
        if m:
            prefix=m.group(1) or '';phase=m.group(2);name=m.group(3);idx=counters.get(phase,0);row=e[idx];counters[phase]=idx+1
            if phase=='dp':
                if row['case'] in ['create','collision']:
                    for suffix in ['lo','hi','kind']:lines.append('clear_array = '+prefix+'__v64a_'+name+'_'+suffix)
                    for suffix in ['ver','gen','len']:lines.append('clear_variable = '+prefix+'__v64a_'+name+'_'+suffix)
                    if row['case']=='collision':lines.append('set_variable = { '+prefix+'__v64a_'+name+'_lo^4095 = 9 }')
                else:
                    for i,value in enumerate(row['stamps']):lines.append('set_variable = { '+prefix+'__v64o_'+name+'_'+('b' if i<4 else 'i')+str(i%4)+' = '+str(value)+' }')
        lines.append(line)
    return '\n'.join(lines).replace('zzads','zzash')+'\n',e
def probe(address,expected):
    js=O.probe(address,{}).replace('const source='+json.dumps(O.expanded()),'const source='+json.dumps(expanded()))
    pos=js.index('const cm=new CModule')
    native=r'''
const eraseNative=new NativeFunction(base.add(0xBC8FC0),'void',['pointer','pointer']);
const putNew=new NativeCallback((c,k,raw)=>{try{const name=k.readUtf8String(),v=Memory.alloc(16);v.writePointer(k);v.add(8).writeU64(name.length);const p=nativeLookup(c,v,0);p.writeS64(raw);writes.push({op:'put',key:name,raw:raw.toString()});return 1;}catch(e){writes.push({error:String(e)});return 0;}},'int',['pointer','pointer','int64']);
const eraseKey=new NativeCallback((c,k)=>{try{const name=k.readUtf8String(),v=Memory.alloc(16);v.writePointer(k);v.add(8).writeU64(name.length);eraseNative(c,v);writes.push({op:'erase',key:name});return slot(c,name)?0:1;}catch(e){writes.push({error:String(e)});return 0;}},'int',['pointer','pointer']);
'''
    js=js[:pos]+native+js[pos:];js=js.replace('tx_write_existing:writer','tx_write_existing:writer,as_native_put:putNew,as_native_erase:eraseKey')
    at=js.index('function capture(self,ctx)');end=js.index('rpc.exports.samples=()=>rows;',at)
    custom='const expected='+json.dumps(expected)+';\nconst params='+json.dumps(PARAMS)+';\n'+r'''
const workBytes=new NativeFunction(cm.Array64_ShapeBytes,'uint',[])();
const shapeApply=new NativeFunction(cm.Array64_ShapeApply,'int',['pointer','pointer','int','int','int','int64','int','int','pointer','pointer','int','int']);
function map(c){const b=c.add(24).readPointer(),mask=c.add(36).readU32(),spill=c.add(40).readU8(),out={};if(mask>1048575)throw Error('mask');for(let i=0;i<mask+1+spill;i++){const p=b.add(48*i);if(!p.add(4).readU8())continue;const name=txt(p.add(8));if(name)out[name]=p.add(40).readS64().toString();}return out;}
function owned(key,name){const data=['ver','gen','len','lo','hi','kind'].map(s=>'__v64a_'+name+'_'+s);for(let i=0;i<8;i++)data.push('__v64o_'+name+'_'+(i<4?'b':'i')+(i%4));return data.some(root=>key===root||key.startsWith(root+'^'));}
function canonical(m){return JSON.stringify(Object.keys(m).sort().map(k=>[k,m[k]]));}
function without(m,name){const out={};for(const [k,v] of Object.entries(m))if(!owned(k,name))out[k]=v;return out;}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!/^(dp|dq|dr)_tx/.test(n))return;const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const sid=Number(slot(c,'ds_scopeid').readS64().toString())/100000,scope=scopes[sid-1],lineage=new UInt64(slot(c,'ds_lineage').readS64().toString()),row=expected.find(v=>v.scope===scope&&v.name===name);if(!row)throw Error('case');
 const before=map(c),start=writes.length,steps=[];let record=null;
 if(n.startsWith('dp_')){if(!['create','collision'].includes(row.case))record=exportOne(c,name,scope,lineage,2,new UInt64(8000+rows.length));}
 else if(n.startsWith('dq_')){const p=params[row.case],stamps=Memory.alloc(32);row.stamps.forEach((x,i)=>stamps.add(i*4).writeU32(x));const work=Memory.alloc(workBytes);
  const result=shapeApply(c,Memory.allocUtf8String(name),p[0],p[1],p[2],new Int64(p[3]),p[4],p[5],stamps,work,p[6],p[7]);steps.push({key:'shape',result});}
 const afterMap=map(c);rows.push({phase:n.slice(0,2),name,scope,container:c.toString(),record,old:null,steps,after:group(c,name),beforeMap:before,afterMap,exactRollback:canonical(before)===canonical(afterMap),unrelatedUnchanged:canonical(without(before,name))===canonical(without(afterMap,name)),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
'''
    return js[:at]+custom+js[end:]
def execute(out,phase):
    import frida
    e=json.loads(R.read(out/'expected.json'));addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1]
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8');s=frida.attach(R.FH.find_pid());sc=s.create_script(probe(addr,e));commands=[]
    try:
        sc.load()
        for event in (['zzash.1','zzash.2'] if phase=='write' else ['zzash.3']):
            x=sc.exports_sync.exec('event',[event]);print(x,flush=True);commands.append({'input':'event '+event,'stdout':x});assert 'out->ok     = 1' in x
            if event=='zzash.1':
                samples=[v for v in sc.exports_sync.samples() if v.get('record')];D.persist(out,samples)
                # Absence/collision are explicitly journaled, not represented as an invented baseline.
                (out/'absent_preflight.json').write_text(json.dumps([v for v in sc.exports_sync.samples() if not v.get('record')],indent=2),encoding='utf-8');commands.append({'input':'reopen durable existing baselines before shape operations','count':len(D.loaded_records(out))})
        (out/(phase+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
        if phase=='write':
            start=time.time();x=sc.exports_sync.exec('savegame',['ash']);print(x,flush=True);commands.append({'input':'savegame ash','stdout':x});assert 'out->ok     = 1' in x
            p=R.DOC/'save games/ash.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
WANT={'create':['-9223372036854775808']*2,'append':['1234567890112500','-1','9223372036854775807'],'insert':['1234567890112500','-9223372036854775808','-1'],'erase':['-1'],'resizeup':['1234567890112500','-1','250000','250000'],'resizedown':['1234567890112500'],'rollback':['1234567890112500','-1']}
def verify(out):
    e=json.loads(R.read(out/'expected.json'));rows=[]
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'));selected=[v for v in samples if v.get('phase')==('dq' if phase=='write' else 'dr')]
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()});rows.append({'key':phase+'.captures','ok':len(samples)==(100 if phase=='write' else 50) and len(selected)==50 and not any('error' in s for s in samples)})
        for expect,s in zip(e,selected):
            case=expect['case'];h=s.get('after',{}).get('head',{});ok=s.get('scope')==expect['scope'] and s.get('unrelatedUnchanged')
            if case in WANT:ok=ok and h.get('status')==1 and h.get('generation')==(2 if case in ['create','rollback'] else 4) and [v['raw'] for v in s['after']['values']]==WANT[case]
            elif case=='clear':ok=ok and h.get('status')==0
            elif case=='collision':ok=ok and h.get('status')==-3
            else:ok=ok and h.get('status')==-5
            if phase=='write':ok=ok and s['steps'][0]['result']==(2 if case=='rollback' else -3 if case=='quarantine' else -2 if case=='collision' else 1) and (case not in ['rollback','collision'] or s['exactRollback']) and not any('error' in v for v in s.get('writes',[]))
            else:ok=ok and s.get('exactRollback') and not s.get('writes')
            rows.append({'key':phase+'.'+expect['label']+'.'+case,'ok':bool(ok),'observed':s})
            m=re.findall(r'DS '+re.escape(expect['label']+'.'+case)+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g);rows.append({'key':phase+'.'+expect['label']+'.'+case+'.native','ok':bool(m) and m[-1]==('12345678901.125','2.5','7.75')})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_shape' in l];rows.append({'key':'parser_errors','ok':not errors});rows.append({'key':'baseline_record_reopen','ok':len(D.loaded_records(out))==40})
    r={'checks':len(rows),'passed':sum(v['ok'] for v in rows),'rows':rows,'errors':errors,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_api':False,'rollback_comparison':'complete scoped key/raw map; bucket addresses and allocator layout not required equal'};r['exit']=int(r['checks']!=r['passed'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([v for v in rows if not v['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_shape'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_shape.txt').write_text(text,encoding='utf-8')
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write')
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload');return verify(out)
if __name__=='__main__':raise SystemExit(main())
