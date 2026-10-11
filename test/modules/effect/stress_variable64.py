"""Deterministic game-level stress fixtures; every assertion has an exact raw oracle."""
import argparse
from decimal import Decimal, getcontext
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

getcontext().prec=60
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/tools'))
sys.path.insert(0,str(ROOT/'test/lib'))
import hoi4_launch as HL
import frida_host as FH
DOC=Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
GL=DOC/'logs/game.log'
PL=Path(HL.LOG)
MAX=9223372036854775807
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def raw(x):return int(Decimal(str(x))*100000)
def number(x):return format(Decimal(x)/100000,'f')
def fixtures(extended=False):
    events=[];expected={};counts={};operations=0
    def event(n,lines):
        events.append('country_event = { id = zzv64stress.%d hidden = yes is_triggered_only = yes immediate = {\n%s\n log = "VST DONE e%d"\n} option = { name = zzv64stress.%d.a } }'%(n,'\n'.join(lines),n,n))
    def check(lines,key,name,value):
        expected[key]=str(value);lines.append('log = "VST %s=[?%s|5]"'%(key,name))
    def set64(lines,name,value):lines.append('set_variable64 = { var = %s value = %s }'%(name,value))
    setup=['set_variable = { st_marker = 1202601 }']
    for name,value in [('st_big','5000000000.125'),('st_small','1.5'),('st_neg','-1.5'),('st_zero','0'),('st_operand','2.5')]:set64(setup,name,value)
    event(1,setup)
    post=[]
    check(post,'load.marker','st_marker','1202601')
    for name,value in [('st_big','5000000000.125'),('st_small','1.5'),('st_neg','-1.5'),('st_zero','0')]:check(post,'load.'+name,name,value)
    for effect,name,value,result,key in [
        ('add_to_variable','st_big','0.25','5000000000.375','load.add_big'),
        ('add_to_variable','st_small','0.25','1.75','load.add_small'),
        ('subtract_from_variable','st_neg','0.5','-2','load.sub_neg'),
        ('add_to_variable','st_zero','0.125','0.125','load.add_zero'),
        ('multiply_variable','st_small','st_operand','4.375','load.mul_variable'),
        ('divide_variable','st_big','2','2500000000.1875','load.div_big')]:
        post.append('%s = { var = %s value = %s }'%(effect,name,value));check(post,key,name,result)
    post.append('clamp_variable = { var = st_big max = 1000000000.25 }');check(post,'load.clamp','st_big','1000000000.25')
    event(2,post)
    scope=[]
    set64(scope,'st_shared','10.5')
    scope.append('ARI = { set_variable = { st_shared = 7.5 } add_to_variable = { var = st_shared value = 0.25 }')
    check(scope,'scope.vanilla','st_shared','7.75');scope.append('}')
    scope.append('add_to_variable = { var = st_shared value = 0.25 }');check(scope,'scope.original64','st_shared','10.75')
    scope.append('ARI = { clear_variable = st_shared set_variable = { st_shared = 2.5 }')
    check(scope,'scope.clear_plain','st_shared','2.5');scope.append('}')
    scope.append('multiply_variable = { var = st_shared value = 2 }');check(scope,'scope.after_other_set','st_shared','21.5')
    set64(scope,'st_shared64','5000000000.5')
    scope.append('ARI = { set_variable64 = { var = st_shared64 value = -5000000000.25 } add_to_variable = { var = st_shared64 value = 0.125 }')
    check(scope,'scope.second64','st_shared64','-5000000000.125');scope.append('}')
    scope.append('subtract_from_variable = { var = st_shared64 value = 0.25 }');check(scope,'scope.first64','st_shared64','5000000000.25')
    event(3,scope)
    loop=[]
    for i in range(8):set64(loop,'st_loop%d'%i,'100.125')
    for i in range(640):
        name='st_loop%d'%(i%8)
        for effect,value in [('add_to_variable','0.125'),('multiply_variable','2'),('divide_variable','2'),('subtract_from_variable','0.125')]:
            loop.append('%s = { var = %s value = %s }'%(effect,name,value));operations+=1
    for i in range(8):check(loop,'loop.%d'%i,'st_loop%d'%i,'100.125')
    event(4,loop)
    edge=[]
    for length in [7,8,15,16,30,31,32,33,34,40]:
        name='s'+str(length)+'x'*(length-len(str(length))-1)
        edge.append('set_variable = { %s = 42 }'%name)
        set64(edge,name,'12345.125')
        if length<=33:
            edge.append('add_to_variable = { var = %s value = 0.25 }'%name);check(edge,'name.%d'%length,name,'12345.375')
        else:check(edge,'name.reject%d'%length,name,'42')
    for name,value,effect,operand,result in [
        ('st_upper','92233720368547.75807','add_to_variable','0.00001','92233720368547.75807'),
        ('st_lower','-92233720368547.75807','subtract_from_variable','0.00001','-92233720368547.75807'),
        ('st_mulo','50000000000000','multiply_variable','4','92233720368547.75807'),
        ('st_divo','50000000000000','divide_variable','0.00001','92233720368547.75807'),
        ('st_zero_div','-1.125','divide_variable','0','-1.125')]:
        set64(edge,name,value);edge.append('%s = { var = %s value = %s }'%(effect,name,operand));check(edge,'edge.'+name,name,result)
    edge += ['set_variable = { st_plain = 10.5 }','add_to_variable = { var = st_plain value = 0.25 }','multiply_variable = { var = st_plain value = 2 }']
    check(edge,'vanilla.plain','st_plain','21.5')
    set64(edge,'st_reclaim','9876543210.125')
    edge+=['set_variable = { st_reclaim = 7.5 }','add_to_variable = { var = st_reclaim value = 0.25 }'];check(edge,'vanilla.reclaim','st_reclaim','7.75')
    for name,value in [('temp_army_manpower_factor','3.5'),('st_suffix_f','4.5'),('st_suffix_hi','5.5')]:
        edge+=['set_variable = { %s = %s }'%(name,value),'add_to_variable = { var = %s value = 0.25 }'%name];check(edge,'vanilla.'+name,name,str(Decimal(value)+Decimal('.25')))
    event(5,edge)
    fuzz=[];rng=random.Random(12026)
    for i in range(128):
        a=rng.randint(-10**12,10**12);b=rng.randint(-1000000,1000000) or 1
        op=['add_to_variable','subtract_from_variable','multiply_variable','divide_variable'][i%4]
        result=a+b if i%4==0 else a-b if i%4==1 else (abs(a*b)//100000)*(1 if a*b>=0 else -1) if i%4==2 else (abs(a*100000)//abs(b))*(1 if a*b>=0 else -1)
        set64(fuzz,'st_fuzz',number(a));set64(fuzz,'st_fuzzop',number(b))
        fuzz.append('%s = { var = st_fuzz value = st_fuzzop }'%op);check(fuzz,'fuzz.%d'%i,'st_fuzz',number(result));operations+=1
    event(6,fuzz)
    capacity=[]
    for i in range(192):
        name='st_cap%03d'%i;set64(capacity,name,'5000000000.125')
        capacity.append('add_to_variable = { var = %s value = 0.25 }'%name);check(capacity,'capacity.%d'%i,name,'5000000000.375');operations+=1
    for i in [0,1,63,127,128,191]:
        name='st_cap%03d'%i;capacity.append('multiply_variable = { var = %s value = 2 }'%name);check(capacity,'capacity.revisit%d'%i,name,'10000000000.75')
    event(7,capacity)
    if extended:
        debts=[]
        set64(debts,'st_debtop','5000000000')
        for i in range(70):
            n='st_debt%03d'%i
            debts+=['set_variable = { %s = 100 }'%n,'add_to_variable = { var = %s value = st_debtop }'%n]
            check(debts,'debts.lock%d'%i,n,'2147483647.99999')
        for i in range(70):
            n='st_debt%03d'%i
            debts+=['divide_variable = { var = %s value = 100000 }'%n]
            check(debts,'debts.settle%d'%i,n,'50000.001')
        debts+=['set_variable = { st_scopeddebt = 100 }','add_to_variable = { var = st_scopeddebt value = st_debtop }',
                'ARI = { set_variable = { st_scopeddebt = 10 } add_to_variable = { var = st_scopeddebt value = 0.25 }']
        check(debts,'debts.other_scope','st_scopeddebt','10.25');debts.append('}')
        debts.append('divide_variable = { var = st_scopeddebt value = 100000 }');check(debts,'debts.scope_settle','st_scopeddebt','50000.001')
        event(8,debts)
        extra=['set_variable = { st_fake = 7.5 }','set_variable = { st_fake_var64f = 1.5 }','set_variable = { st_fake_var64h = 0 }','add_to_variable = { var = st_fake value = 0.25 }']
        check(extra,'extras.fake_format','st_fake','7.75')
        set64(extra,'st_clear','5000000000.125');extra.append('clear_variable = st_clear');check(extra,'extras.clear64','st_clear','0')
        event(9,extra)
    body='add_namespace = zzv64stress\n'+'\n'.join(events)+'\n'
    operations=len(re.findall(r'\b(?:add_to_variable|subtract_from_variable|multiply_variable|divide_variable)\s*=',body))
    return body,expected,{'arithmetic_calls':operations,'assertions':len(expected),'seed':12026}

def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def capture(out,label):
    for p,n in [(GL,'game'),(PL,'plugin'),(DOC/'logs/error.log','error')]:
        if p.exists():(out/(label+'_'+n+'.log')).write_bytes(p.read_bytes())
def ready(reload=False):
    deadline=time.time()+240
    while time.time()<deadline:
        if ('End RestoreDeviceObjects' if reload else 'Launching SINGLEPLAYER-game') in read(GL):
            time.sleep(32);return
        if not HL.proc_alive():raise RuntimeError('game died while waiting')
        time.sleep(.5)
    raise TimeoutError('game readiness')
def execute_batch(ids,out,label):
    pid,session,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False)
    records=[]
    try:
        for n in ids:
            before=read(GL).count('VST DONE e%d'%n);t=time.monotonic()
            result=sc.exports_sync.exec('event',['zzv64stress.%d'%n]);print(result,flush=True)
            if 'out->ok     = 1' not in result:raise RuntimeError(result)
            deadline=time.monotonic()+90
            while read(GL).count('VST DONE e%d'%n)<=before:
                if not HL.proc_alive():raise RuntimeError('game died during event')
                if time.monotonic()>deadline:raise TimeoutError('event %d'%n)
                time.sleep(.1)
            dt=time.monotonic()-t;records.append({'event':n,'seconds':dt,'result':result});print('EVENT_FINISHED',n,dt,flush=True)
        if label=='setup':
            t=time.time();result=sc.exports_sync.exec('savegame',['v64stress']);records.append({'savegame':result});print(result,flush=True)
            if 'out->ok     = 1' not in result:raise RuntimeError(result)
            sv=DOC/'save games/v64stress.hoi4'
            deadline=time.time()+30
            while not sv.exists() or sv.stat().st_mtime<t:
                if time.time()>deadline:raise TimeoutError('fresh save')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(sv.read_bytes())
    finally:FH.detach(session)
    capture(out,label);(out/(label+'_commands.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    return records
def verify(out):
    import re
    expected=json.loads((out/'expected.json').read_text(encoding='utf-8'));g=read(out/'stress_game.log')
    observed={key:value for key,value in re.findall(r'VST ([^\s=]+)=([^\s]+)',g)}
    rows=[]
    for key,want in expected.items():
        value=observed.get(key);ok=False
        try:ok=Decimal(value)==Decimal(want)
        except (TypeError,ValueError,ArithmeticError):pass
        rows.append({'key':key,'expected':want,'observed':value,'ok':ok})
    result={'checks':len(rows),'passed':sum(r['ok'] for r in rows),'failed':[r for r in rows if not r['ok']],'rows':rows}
    (out/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))
    return not result['failed']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--verify-only',action='store_true');ap.add_argument('--extended',action='store_true');args=ap.parse_args()
    out=ROOT/'test/reports/20261012_variable64_transaction/stress'/args.phase;out.mkdir(parents=True,exist_ok=True)
    if args.verify_only:return 0 if verify(out) else 1
    if (out/'expected.json').exists():raise RuntimeError('phase already exists; preserve evidence and choose a fresh phase')
    body,expected,info=fixtures(args.extended);(out/'events.txt').write_text(body,encoding='utf-8');(out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    (out/'info.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print('MATRIX',info,flush=True)
    (DOC/'mod/bakaifa/events/zz_variable64_stress.txt').write_text(body,encoding='utf-8')
    HL.kill();capture(out,'before');print('DEPLOY',HL.deploy(),flush=True)
    for f in HL.DEPLOY:print('DLL',f,hashlib.sha256((Path(HL.ROOT)/f).read_bytes()).hexdigest(),flush=True)
    HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready()
    execute_batch([1],out,'setup')
    HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True)
    capture(out,'reload_before')
    execute_batch([2,3,4,5,6,7]+([8,9] if args.extended else []),out,'stress')
    print('FINISHED alive=',HL.proc_alive(),flush=True)
    return 0 if verify(out) else 1
if __name__=='__main__':raise SystemExit(main())
