import argparse,hashlib,inspect,json,pathlib,re,secrets,sys,time
import verify_array64_durable as D
T=D.T;R=D.R;ROOT=D.ROOT;TX=D.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_ownership_gate.c'
CASES=['good','foreign','missingstamp','recreate','nofile']
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_durable_snapshot.c"',D.expanded())
def fixtures():
    body=inspect.getsource(D.fixtures).replace('def fixtures():','def build():').replace("['persist','stale']",repr(CASES));ns=dict(vars(D));exec(body,ns);text,e=ns['build']()
    branch=[secrets.randbelow(2147483646)+1 for _ in range(4)]
    for row in e:row['stamps']=branch+[secrets.randbelow(2147483646)+1 for _ in range(4)]
    counters={};lines=[];marker=None
    for line in text.splitlines():
        match=re.search(r'var = (global\.)?(d[pqr])_(tx\w+)',line)
        if match:
            prefix=match.group(1) or '';phase=match.group(2);name=match.group(3);index=counters.get(phase,0);row=e[index];counters[phase]=index+1
            if phase=='dp':
                for i,v in enumerate(row['stamps']):lines.append('set_variable = { '+prefix+'__v64o_'+name+'_'+('b' if i<4 else 'i')+str(i%4)+' = '+str(v)+' }')
            if phase=='dq':
                if row['case']=='foreign':lines.append('set_variable = { '+prefix+'__v64o_'+name+'_b0 = '+str(row['stamps'][0]%2147483647+1)+' }')
                elif row['case']=='missingstamp':lines.append('clear_variable = '+prefix+'__v64o_'+name+'_i0')
                elif row['case']=='recreate':
                    # Actual native clear/recreate with unchanged name, length and starting generation.
                    root=prefix+'__v64a_'+name
                    for suffix in ['lo','hi','kind']:lines.append('clear_array = '+root+'_'+suffix)
                    for suffix in ['ver','gen','len']:lines.append('clear_variable = '+root+'_'+suffix)
                    for suffix,v in [('ver',2),('gen',2),('len',2)]:lines.append('set_variable = { '+root+'_'+suffix+' = '+str(v)+' }')
                    for col,suffix in enumerate(['lo','hi','kind']):
                        for triple in [T.G.split(-9223372036854775808),T.G.split(-1)]:lines.append('add_to_array = { array = '+root+'_'+suffix+' value = '+str(triple[col])+' }')
                    lines.append('set_variable = { '+prefix+'__v64o_'+name+'_i0 = '+str(row['stamps'][4]%2147483647+1)+' }')
        lines.append(line)
    return '\n'.join(lines).replace('zzads','zzaog')+'\n',e
def probe(address,records):
    js=D.probe(address,records).replace('const source='+json.dumps(D.expanded()),'const source='+json.dumps(expanded()))
    js=js.replace('cm.Array64_ExportBaseline','cm.Array64_ExportOwned').replace('cm.Array64_ImportBaseline','cm.Array64_ImportOwned')
    at=js.index('function capture(self,ctx)');end=js.index('rpc.exports.samples=()=>rows;',at)
    custom=r'''
function ownedImport(c,name,scope,lineage,hex,owner){if(hex===null){const snap=Memory.alloc(size);return{result:importRecord(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,owner,ptr(0),0,snap),snap};}return importOne(c,name,scope,lineage,hex,owner);}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!/^(dp|dq|dr)_tx/.test(n))return;const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const sid=Number(slot(c,'ds_scopeid').readS64().toString())/100000,lineage=new UInt64(slot(c,'ds_lineage').readS64().toString()),scope=scopes[sid-1],owner=new UInt64(7000+rows.length),before=snap(c),protectedBefore=protectedSnap(c,name),start=writes.length,key=scope+'|'+name,steps=[];let record=null;
 if(n.startsWith('dp_')){record=exportOne(c,name,scope,lineage,2,owner);prepared.set(key,{generation:2});}
 else if(n.startsWith('dq_')){const result=setGroup(c,Memory.allocUtf8String(name),0,2,new Int64('9223372036854775807'),1,5,1);steps.push({key:'quarantine',result});}
 else{
   if(!records[key])throw Error('record index missing');const beforeTest=snap(c),w=writes.length,loaded=ownedImport(c,name,scope,lineage,records[key].record,owner);
   const want=name==='txgood'?1:name==='txforeign'?-14:name==='txmissingstamp'?-13:name==='txrecreate'?-15:-10;
   steps.push({key:'ownership',result:loaded.result,want,noWrite:beforeTest===snap(c)&&w===writes.length});
   if(loaded.result===1){const result=recover(c,Memory.allocUtf8String(name),owner,loaded.snap,0);steps.push({key:'recover',result});}
 }
 rows.push({phase:n.slice(0,2),name,scope,container:c.toString(),record,old:null,steps,after:group(c,name),onlyExpectedSlotsChanged:protectedBefore===protectedSnap(c,name),sameBytes:before===snap(c),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
'''
    return js[:at]+custom+js[end:]
def loaded_records(out):
    manifest=json.loads(R.read(out/'records.json'));data={}
    for key,info in manifest.items():
        p=pathlib.Path(info['record_path']);missing=key.endswith('|txnofile')
        if missing:assert not p.exists();data[key]={'record':None};continue
        b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==info['record_sha256'];data[key]={'record':b.hex()}
    return data
def execute(out,phase):
    import frida
    addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1];records=loaded_records(out) if phase=='reload' else {}
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8');session=frida.attach(R.FH.find_pid());script=session.create_script(probe(addr,records));commands=[]
    try:
        script.load()
        for event in (['zzaog.1','zzaog.2'] if phase=='write' else ['zzaog.3']):
            x=script.exports_sync.exec('event',[event]);print(x,flush=True);commands.append({'input':'event '+event,'stdout':x});assert 'out->ok     = 1' in x
            if event=='zzaog.1':D.persist(out,script.exports_sync.samples());commands.append({'input':'persist owned baselines before lifecycle mutation','count':25})
        (out/(phase+'_samples.json')).write_text(json.dumps(script.exports_sync.samples(),indent=2),encoding='utf-8')
        if phase=='write':
            manifest=json.loads(R.read(out/'records.json'))
            for key,info in manifest.items():
                if key.endswith('|txnofile'):
                    p=pathlib.Path(info['record_path']);backup=p.with_suffix('.removed');p.replace(backup);assert not p.exists() and hashlib.sha256(backup.read_bytes()).hexdigest()==info['record_sha256']
            start=time.time();x=script.exports_sync.exec('savegame',['aog']);print(x,flush=True);commands.append({'input':'savegame aog','stdout':x});assert 'out->ok     = 1' in x
            p=R.DOC/'save games/aog.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(session)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    expected=json.loads(R.read(out/'expected.json'));rows=[];manifest=json.loads(R.read(out/'records.json'))
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'));selected=[s for s in samples if s.get('phase')==('dq' if phase=='write' else 'dr')]
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()});rows.append({'key':phase+'.captures','ok':len(samples)==(50 if phase=='write' else 25) and len(selected)==25 and not any('error' in s for s in samples)})
        for e,s in zip(expected,selected):
            h=s.get('after',{}).get('head',{});ok=s.get('scope')==e['scope'] and s.get('name')==e['name']
            if phase=='write':ok=ok and h.get('status')==-5 and s['steps'][0]['result']==-3
            elif e['case']=='good':ok=ok and h.get('generation')==4 and [v['raw'] for v in s['after']['values']]==['1234567890112500','-1'] and s['steps'][0]['result']==1 and s['steps'][1]['result']==1
            else:ok=ok and h.get('status')==-5 and s.get('sameBytes') and not s.get('writes') and s['steps'][0]['result']==s['steps'][0]['want']
            rows.append({'key':phase+'.'+e['label']+'.'+e['case'],'ok':bool(ok),'observed':s})
            m=re.findall(r'DS '+re.escape(e['label']+'.'+e['case'])+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g);rows.append({'key':phase+'.'+e['label']+'.'+e['case']+'.native','ok':bool(m) and m[-1]==('12345678901.125','2.5','7.75')})
    for key,info in manifest.items():
        p=pathlib.Path(info['record_path']);p=p.with_suffix('.removed') if key.endswith('|txnofile') else p;b=p.read_bytes();inner=b[48:-8]
        h=14695981039346656037
        for ch in b[:-8]:h=((h^ch)*1099511628211)&((1<<64)-1)
        decoded=D.inspect_record(inner,key);rows.append({'key':'owned_file.'+key,'ok':b[:8]==b'A64OWN02' and int.from_bytes(b[8:12],'little')==1 and int.from_bytes(b[12:16],'little')==len(inner) and h==int.from_bytes(b[-8:],'little') and decoded['generation']==2 and hashlib.sha256(b).hexdigest()==info['record_sha256']})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_ownership' in l];rows.append({'key':'parser_errors','ok':not errors});rows.append({'key':'missing_no_fallback','ok':len(loaded_records(out))==25})
    r={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_api':False,'tokens':'Four randomized safe-positive31-bit words each for branch and group incarnation; branch mutation explicit fixture action, not automatic fork detection'};r['exit']=int(r['checks']!=r['passed'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([x for x in rows if not x['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_ownership'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_ownership.txt').write_text(text,encoding='utf-8')
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write')
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload');return verify(out)
if __name__=='__main__':raise SystemExit(main())
