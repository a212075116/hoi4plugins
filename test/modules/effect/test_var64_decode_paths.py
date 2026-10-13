"""Test real scoped read/decode routing against independent integer and trace oracles."""
import argparse
import hashlib
import json
import random

from test_var64_text_refactor import VCVARS, execute, function
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();source=args.source.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    text=source.read_text(encoding='utf-8-sig')
    header=source.parent/'variable64_math.h'
    math='#include "'+header.as_posix()+'"\n' if header.exists() else '#define VAR64_SLOT_SCALE 100000LL\n#define VAR64_FRAC_SCALE 100000LL\n#define VAR64_FRAC_BIAS 100000LL\n'
    code=function(text,'Var64_ReadStoredIn')
    fixture=r'''
#include <stdio.h>
#include <string.h>
#include "NAME_HEADER"
MATH
static long long lowValue,highValue,fractionValue;
static int flags,sequence;
static int Var64_LookupInScope(void* c,const char* name,long long* out){int which=strstr(name,"_var64f")?1:strstr(name,"_var64h")?2:3;(void)c;sequence=sequence*10+which;if(flags&(which==1?1:which==2?2:4))return 0;*out=which==1?fractionValue:which==2?highValue:lowValue;return 1;}
READER
int main(void){while(scanf_s("%lld %lld %lld %d",&lowValue,&highValue,&fractionValue,&flags)==4){long long out=333;int ok;sequence=0;ok=Var64_ReadStoredIn(flags&16?NULL:(void*)1,flags&32?"":flags&64?"abcdefghijklmnopqrstuvwxyz01234567":"value",flags&8?NULL:&out);printf("%d %lld %d\n",ok,out,sequence);}return 0;}
'''.replace('NAME_HEADER',(source.parent/'variable64_name.h').as_posix()).replace('MATH',math).replace('READER',code)
    (output/'fixture.c').write_text(fixture,encoding='ascii')
    command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    maximum=2**63-1;minimum=-2**63;randomizer=random.Random(20261015)
    values=[minimum,minimum+1,-1,0,1,maximum-1,maximum]+[randomizer.randint(minimum,maximum) for _ in range(2000)]
    cases=[]
    def signed32(value):return (value+2**31)%2**32-2**31
    for raw in values:
        integer=abs(raw)//100000*(-1 if raw<0 else 1);fraction=raw-integer*100000
        for flag in [0,8,1,2,4,16,32,64]:cases.append((signed32(integer)*100000,signed32(integer>>32)*100000,(fraction+100000)*100000,flag))
    metadata=[minimum,maximum,-214748364800001,-214748364800000,-1,0,214748364700000,214748364700001]
    fractions=[-1,0,1,99999,100000,100001,10000000000,19999900000,20000000000]
    cases.extend((low,high,fraction,flag) for low in metadata for high in metadata for fraction in fractions for flag in [0,8])
    for _ in range(4096):cases.append((randomizer.choice(metadata),randomizer.choice(metadata),randomizer.choice(fractions),randomizer.randrange(128)))
    def oracle(low,high,fraction,flag):
        if flag&(16|32|64):return (0,333,0)
        if flag&1 or not(0<fraction<20000000000) or fraction%100000:return (0,333,1)
        if flag&2:return (0,333,12)
        if flag&4:return (0,333,123)
        if low%100000 or high%100000 or not(-2**31<=low//100000<=2**31-1) or not(-2**31<=high//100000<=2**31-1):return (0,333,123)
        if flag&8:return (1,333,123)
        integer=((high//100000)&0xffffffff)<<32|((low//100000)&0xffffffff)
        if integer>=2**63:integer-=2**64
        raw=integer*100000+fraction//100000-100000
        return (1,raw,123) if minimum<=raw<=maximum else (0,333,123)
    inputs=''.join('%d %d %d %d\n'%case for case in cases).encode('ascii');(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs);(output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr)
    observed=[tuple(map(int,line.split())) for line in process.stdout.decode('ascii').splitlines()]
    failures=[dict(index=i,input=case,expected=oracle(*case),observed=observed[i] if i<len(observed) else None) for i,case in enumerate(cases) if i>=len(observed) or observed[i]!=oracle(*case)]
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),seed=20261015,cases=len(cases),passed=len(cases)-len(failures),failures=failures,
                input_sha256=hashlib.sha256(inputs).hexdigest(),build=build,result=result,exit=int(bool(failures) or process.returncode!=0 or len(observed)!=len(cases)),
                scope='Actual stored read and decode; lookup is modeled; independent Python integer/routing oracle includes NULL-output identity semantics; no game process')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='failures'},ensure_ascii=False,indent=2));return record['exit']


if __name__=='__main__':
    raise SystemExit(main())
