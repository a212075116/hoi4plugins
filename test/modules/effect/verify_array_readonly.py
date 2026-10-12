import argparse, hashlib, json, pathlib, re, sys, time
from decimal import Decimal
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'test/lib'), str(ROOT/'test/tools')]
import frida
import frida_host as FH
import hoi4_launch as HL
from verify_array_native_lifecycle import DOC, read, ready
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SOURCE = ROOT/'src/plugin/SDK_RVA/variable64/native_array_readonly.c'

def fixture():
    scopes = [('country', '', '', ['2.5', '-0.125', '7.75']),
              ('other', 'ARI', '', ['9.25']), ('state', '335', '', ['-2', '0']),
              ('character', 'ABY_Hoshino', '', ['4.5']), ('global', '', 'global.', ['6.125'])]
    write = ['add_namespace = zzarrayread', 'country_event = { id = zzarrayread.1 hidden = yes is_triggered_only = yes immediate = {']
    reload = ['country_event = { id = zzarrayread.2 hidden = yes is_triggered_only = yes immediate = {']
    expected = []
    for label, scope, prefix, values in scopes:
        if scope: write.append(scope+' = {'); reload.append(scope+' = {')
        name = prefix+'ro_array'
        write.extend(['clear_array = '+name, 'set_variable64 = { var = '+name+' value = 12345678901.125 }'])
        for value in values: write.append('add_to_array = { array = '+name+' value = '+value+' }')
        for lines in [write, reload]:
            for index, value in enumerate(values):
                key = label+'.'+str(index)
                lines.extend(['set_variable = { ro_ok = 0 }',
                    'if = { limit = { check_variable = { var = '+name+'^'+str(index)+' value = '+value+' compare = equals } } set_variable = { ro_ok = 1 } }',
                    'if = { limit = { plugin_check_variable64 = { var = '+name+'^'+str(index)+' value = '+value+' compare = equals } } log = "AR '+key+' native=[?ro_ok] value=[?'+name+'^'+str(index)+'] scalar=[?'+name+'] count=[?'+name+'^num]" }'])
            # Both absent and empty are probed in the same scoped native container.
            lines.append('if = { limit = { plugin_check_variable64 = { var = '+prefix+'ro_missing value = 0 compare = equals } } log = "AR missing '+label+'" }')
        expected.append({'label':label, 'name':'ro_array', 'values':values})
        if scope: write.append('}'); reload.append('}')
    write.extend(['clear_array = ro_empty', 'add_to_array = { array = ro_empty value = 1 }', 'clear_array = ro_empty',
        'if = { limit = { plugin_check_variable64 = { var = ro_empty value = 0 compare = equals } } log = "AR empty" }',
        'set_variable = { ro_marker = 20261012 }', 'log = "AR WRITE DONE"', '} option = { name = zzarrayread.1.a } }'])
    reload.extend(['if = { limit = { plugin_check_variable64 = { var = ro_empty value = 0 compare = equals } } log = "AR empty" }',
        'log = "AR marker=[?ro_marker]"', 'log = "AR RELOAD DONE"', '} option = { name = zzarrayread.2.a } }'])
    longname='__v64a_abcdefghijklmnopqrst_kind'
    setup=['clear_array = '+longname,'add_to_array = { array = '+longname+' value = 1 }']
    observe=['if = { limit = { plugin_check_variable64 = { var = '+longname+'^0 value = 1 compare = equals } } log = "AR long value=[?'+longname+'^0] count=[?'+longname+'^num]" }']
    write[-4:-4]=setup+observe
    reload[-3:-3]=observe
    return '\n'.join(write+reload)+'\n', expected

def probe_js(address):
    base = (ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')
    return base+'\nconst source = '+json.dumps(SOURCE.read_text(encoding='utf-8'))+';\n'+r'''
const base = Process.getModuleByName('hoi4.exe').base;
const reader = new NativeCallback(function(src,dst,n) {
 try { const size=n.toNumber(); if(size<0||size>4096)return 0; const bytes=src.readByteArray(size);dst.writeByteArray(bytes);return 1; } catch(e){return 0;}
},'int',['pointer','pointer','uint64']);
const module = new CModule(source,{na_read_memory:reader});
const arrayRead = new NativeFunction(module.NativeArray_Read,'int',['pointer','pointer','int','pointer','pointer']);
const resolve = new NativeFunction(base.add(0x542500),'pointer',Array(10).fill('pointer'));
const rows=[];
function str(p){const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();if(n>100)throw Error('name length');return(cap<=15?p:p.readPointer()).readUtf8String(n);}
function bytes(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(x=>x.toString(16).padStart(2,'0')).join('');}
function snapshot(c){const b=c.add(24).readPointer(),mask=c.add(36).readU32(),spill=c.add(40).readU8();if(mask>1048575)throw Error('mask');return bytes(c,48)+bytes(b,48*(mask+1+spill));}
function one(c,name,index){const text=Memory.allocUtf8String(name),v=Memory.alloc(8),n=Memory.alloc(4);v.writeS64(123);n.writeS32(-99);const status=arrayRead(c,text,index,v,n);return {status,count:n.readS32(),raw:v.readS64().toString()};}
function capture(self,ctx){try {
 const d=self.add(88),name=str(d.add(112));if(!name.startsWith('ro_')&&!name.startsWith('__v64a_'))return;
 const extra=Array.from({length:8},()=>Memory.alloc(8));const c=resolve(d,ctx,...extra);
 const before=snapshot(c),bounds=one(c,name,-1),values=[];
 if(bounds.status===2)for(let i=0;i<bounds.count;i++)values.push(one(c,name,i));
 const upper=one(c,name,bounds.count),absent=one(c,'ro_never_created',0);
 rows.push({name,container:c.toString(),bounds,upper,absent,values,noMutation:before===snapshot(c)});
 }catch(e){rows.push({error:String(e)});}}
rpc.exports.samples=function(){return rows;};
''' + "\nInterceptor.attach(ptr('0x"+address+"'),{onEnter(a){capture(a[0],a[1]);}});"

def execute(out, phase, event, save=False):
    address = re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)', read(pathlib.Path(HL.LOG)))[-1]
    (out/(phase+'_backend.c')).write_bytes(SOURCE.read_bytes())
    session = frida.attach(FH.find_pid()); script = session.create_script(probe_js(address)); commands = []
    try:
        script.load()
        text = script.exports_sync.exec('event', [event]); print(text, flush=True)
        commands.append({'input':'event '+event,'stdout':text}); assert 'out->ok     = 1' in text
        time.sleep(.5)
        (out/(phase+'_samples.json')).write_text(json.dumps(script.exports_sync.samples(),indent=2),encoding='utf-8')
        if save:
            start=time.time(); text=script.exports_sync.exec('savegame',['arreadonly']);print(text,flush=True)
            commands.append({'input':'savegame arreadonly','stdout':text});assert 'out->ok     = 1' in text
            path=DOC/'save games/arreadonly.hoi4';end=time.time()+30
            while not path.exists() or path.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(path.read_bytes())
    finally: FH.detach(session)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for path,name in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
        if path.exists():(out/(phase+'_'+name+'.log')).write_bytes(path.read_bytes())

def verify(out):
    expected=json.loads(read(out/'expected.json'));checks=[];identities={}
    for phase in ['write','reload']:
        samples=json.loads(read(out/(phase+'_samples.json')));g=read(out/(phase+'_game.log'))
        arrays=[s for s in samples if s.get('name')=='ro_array'];pos=0;containers=[];raw_by_container={}
        checks.append({'key':phase+'.probe_errors','ok':not any('error' in s for s in samples),'samples':len(samples)})
        checks.append({'key':phase+'.exact_backend_source','ok':(out/(phase+'_backend.c')).read_bytes()==SOURCE.read_bytes()})
        for e in expected:
            group=arrays[pos:pos+len(e['values'])];pos+=len(e['values'])
            raw=[str(int(Decimal(v)*100000)) for v in e['values']]
            good=len(group)==len(e['values']) and all(s['bounds']['status']==2 and s['bounds']['count']==len(raw) and
                [v['raw'] for v in s['values']]==raw and all(v['status']==1 for v in s['values']) and s['upper']['status']==2 and
                s['absent']['status']==0 and s['absent']['raw']=='123' and s['noMutation'] for s in group)
            checks.append({'key':phase+'.'+e['label']+'.backend','ok':good})
            if group:
                containers.append(group[0]['container']);raw_by_container[group[0]['container']]=raw
            for index,value in enumerate(e['values']):
                match=re.findall(r'AR '+re.escape(e['label']+'.'+str(index))+r' native=(\S+) value=(\S+) scalar=(\S+) count=(\S+)',g)
                good=bool(match) and match[-1][0]=='1' and Decimal(match[-1][1])==Decimal(value) and Decimal(match[-1][2])==Decimal('12345678901.125') and Decimal(match[-1][3])==len(raw)
                checks.append({'key':phase+'.'+e['label']+'.'+str(index)+'.native_oracle','ok':good,'observed':match})
        identities[phase]=containers
        checks.append({'key':phase+'.all_callback_samples','ok':all(s.get('noMutation') for s in samples) and all(
            [v['raw'] for v in s['values']]==raw_by_container.get(s['container']) and all(v['status']==1 for v in s['values']) for s in arrays)})
        checks.append({'key':phase+'.distinct_containers','ok':len(containers)==5 and len(set(containers))==5})
        for name in ['ro_missing','ro_empty']:
            group=[s for s in samples if s.get('name')==name]
            # clear_array may remove the length key entirely; record native distinction rather than invent it.
            good=bool(group) and all(s['noMutation'] and s['bounds']['status'] in [0,2] and (s['bounds']['status']==0 or s['bounds']['count']==0) for s in group)
            checks.append({'key':phase+'.'+name,'ok':good,'states':[s['bounds'] for s in group]})
        group=[s for s in samples if s.get('name')=='__v64a_abcdefghijklmnopqrst_kind']
        good=bool(group) and all(s['bounds']['status']==2 and s['bounds']['count']==1 and s['values']==[{'status':1,'count':1,'raw':'100000'}] and s['noMutation'] for s in group)
        checks.append({'key':phase+'.reserved_long_name','ok':good and 'AR long value=1 count=1' in g})
    errors=[l for phase in ['write','reload'] for l in read(out/(phase+'_error.log')).splitlines() if 'zz_array_readonly' in l]
    checks.append({'key':'restart_marker','ok':'AR marker=20261012' in read(out/'reload_game.log')})
    checks.append({'key':'no_fixture_errors','ok':not errors})
    result={'checks':len(checks),'passed':sum(x['ok'] for x in checks),'rows':checks,'errors':errors,'identities':identities,
        'alive':HL.proc_alive(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'production_write_enabled':False,
        'backend_execution':'actual C source compiled in Frida CModule; memory copy adapter only; synchronous native event scope'}
    result['exit']=int(result['checks']!=result['passed'] or not result['alive'])
    (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return result['exit']

def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    out=ROOT/'test/reports/20261012_variable64_transaction/array_readonly'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve existing phase')
    text,expected=fixture();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    (DOC/'mod/bakaifa/events/zz_array_readonly.txt').write_text(text,encoding='utf-8')
    HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready();execute(out,'write','zzarrayread.1',True)
    HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True);execute(out,'reload','zzarrayread.2');return verify(out)
if __name__=='__main__':raise SystemExit(main())
