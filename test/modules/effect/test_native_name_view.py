"""Run actual Effect token adapter and observe its borrowed native name-view ABI."""
import argparse
import hashlib
import json
from pathlib import Path
from test_var64_text_refactor import VCVARS, execute, function


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    source=args.source.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True);text=source.read_text(encoding='utf-8-sig')
    header=source.parent.parent/'common/native_name_view.h';view=('#include "'+header.as_posix()+'"\n') if header.exists() else ''
    fixture=r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
VIEW
#define RVA_ADD_TOKEN 0x024BB460u
typedef void* (__fastcall *AddTokenFn)(void*,void*,void*);
static int flags,targetId,readCalls,addCalls,pointerMatches;static unsigned long long capturedSize;static const char* expected;
static void* __fastcall Add(void* out,void* view,void* third){const char* data=*(const char**)view;(void)third;++addCalls;capturedSize=*(unsigned long long*)((unsigned char*)view+8);pointerMatches=data==expected&&capturedSize==strlen(data);*(int*)out=targetId;return out;}
static unsigned char* Effect_GetModuleBase(void){return flags&1?NULL:(unsigned char*)((uintptr_t)Add-RVA_ADD_TOKEN);}
static int ConsoleCmd_IsReadable(const void* p,size_t n){(void)p;(void)n;++readCalls;return !(flags&8);}
static int NativeMemory_IsReadable(const void* p,size_t n){return ConsoleCmd_IsReadable(p,n);}
TOKEN
int main(void){int length;while(scanf_s("%d %d %d",&length,&flags,&targetId)==3){char data[576];int out=333,ok;memset(data,'x',length);data[length]=0;expected=data;readCalls=addCalls=pointerMatches=0;capturedSize=0;ok=Effect_AddToken(flags&2?NULL:data,flags&4?NULL:&out);printf("%d %d %d %d %llu %d\n",ok,out,readCalls,addCalls,capturedSize,pointerMatches);}return 0;}
'''.replace('VIEW',view).replace('\nTOKEN\n','\n'+function(text,'Effect_AddToken')+'\n')
    (output/'fixture.c').write_text(fixture,encoding='ascii');command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    cases=[(length,flags,token) for length in [0,1,15,16,32,63,64,511,512] for flags in range(16) for token in [-1,0,1,20000,2147483647]]
    def oracle(length,flags,token):
        if flags&7:return (0,333,0,0,0,0)
        if flags&8:return (0,333,1,0,0,0)
        if not length:return (0,333,1,0,0,0)
        return (int(token!=0),token,1,1,length,1)
    inputs=''.join('%d %d %d\n'%case for case in cases).encode();(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs);(output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr)
    observed=[tuple(map(int,line.split())) for line in process.stdout.decode().splitlines()]
    failures=[dict(index=i,input=case,expected=oracle(*case),observed=observed[i] if i<len(observed) else None) for i,case in enumerate(cases) if i>=len(observed) or observed[i]!=oracle(*case)]
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=len(cases),passed=len(cases)-len(failures),failures=failures,build=build,result=result,input_sha256=hashlib.sha256(inputs).hexdigest(),exit=int(bool(failures) or process.returncode!=0 or len(observed)!=len(cases)),scope='Actual token adapter; modeled module/readability/AddToken; observes borrowed pointer and byte length at native ABI offsets0/8; no game allocation')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='failures'},ensure_ascii=False,indent=2));return record['exit']


if __name__=='__main__':
    raise SystemExit(main())
