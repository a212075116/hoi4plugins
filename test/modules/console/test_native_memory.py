"""Compare the real readability implementation against region and real-page fixtures."""
import argparse
import hashlib
import json
import random
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'effect'))
from test_var64_text_refactor import VCVARS, execute


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source_root',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();root=args.source_root.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    console=root/'src/plugin/SDK_RVA/console/console_cmd.c';text=console.read_text(encoding='utf-8-sig')
    start=text.index('int ConsoleCmd_IsReadable(');end=text.index('void ConsoleCmd_InitResult(',start);code=text[start:end]
    memory=root/'src/plugin/SDK_RVA/common/native_memory.c'
    if memory.exists():code='#include "'+memory.as_posix()+'"\n'+code
    fixture=r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
static MEMORY_BASIC_INFORMATION region;static unsigned calls,failed;static int real;
static SIZE_T WINAPI Query(LPCVOID address,PMEMORY_BASIC_INFORMATION out,SIZE_T size){++calls;if(real)return VirtualQuery(address,out,size);if(failed)return 0;*out=region;return sizeof(*out);}
#define VirtualQuery Query
CODE
static int sanity(void){SYSTEM_INFO info;unsigned char* p;DWORD old;int total=0,passed=0;real=1;GetSystemInfo(&info);p=VirtualAlloc(NULL,3*info.dwPageSize,MEM_RESERVE,PAGE_NOACCESS);if(!p)return 2;
 if(!VirtualAlloc(p,info.dwPageSize,MEM_COMMIT,PAGE_READWRITE)||!VirtualAlloc(p+info.dwPageSize,info.dwPageSize,MEM_COMMIT,PAGE_READONLY))return 3;
#define CHECK(value) do{++total;passed+=!!(value);}while(0)
 CHECK(ConsoleCmd_IsReadable(p,1));CHECK(ConsoleCmd_IsReadable(p,info.dwPageSize));CHECK(ConsoleCmd_IsReadable(p+info.dwPageSize-1,1));
 CHECK(!ConsoleCmd_IsReadable(p+info.dwPageSize-1,2));CHECK(ConsoleCmd_IsReadable(p+info.dwPageSize,info.dwPageSize));CHECK(!ConsoleCmd_IsReadable(p+2*info.dwPageSize,1));
 CHECK(ConsoleCmd_IsReadable(p,0));CHECK(!ConsoleCmd_IsReadable(NULL,0));CHECK(!ConsoleCmd_IsReadable(p,(size_t)-1));
 if(!VirtualProtect(p+info.dwPageSize,info.dwPageSize,PAGE_READWRITE|PAGE_GUARD,&old))return 4;CHECK(!ConsoleCmd_IsReadable(p+info.dwPageSize,1));
 if(!VirtualProtect(p+info.dwPageSize,info.dwPageSize,PAGE_NOACCESS,&old))return 4;CHECK(!ConsoleCmd_IsReadable(p+info.dwPageSize,1));
 if(!VirtualProtect(p,info.dwPageSize,PAGE_EXECUTE,&old))return 4;CHECK(!ConsoleCmd_IsReadable(p,1));
 if(!VirtualProtect(p,info.dwPageSize,PAGE_EXECUTE_READ,&old))return 4;CHECK(ConsoleCmd_IsReadable(p,1));
 if(!VirtualProtect(p,info.dwPageSize,PAGE_EXECUTE_READWRITE,&old))return 4;CHECK(ConsoleCmd_IsReadable(p,1));
 VirtualFree(p,0,MEM_RELEASE);printf("%d/%d actual VirtualAlloc/VirtualProtect readability checks\n",passed,total);return passed!=total;
}
int main(int argc,char** argv){unsigned long long address,length,base,size;DWORD state,protect;(void)argv;if(argc>1)return sanity();
 while(scanf_s("%llu %llu %llu %llu %lu %lu %u",&address,&length,&base,&size,&state,&protect,&failed)==7){int ok;memset(&region,0,sizeof(region));region.BaseAddress=(void*)(uintptr_t)base;region.RegionSize=(SIZE_T)size;region.State=state;region.Protect=protect;calls=0;ok=ConsoleCmd_IsReadable((void*)(uintptr_t)address,(size_t)length);printf("%d %u\n",ok,calls);}return 0;}
'''.replace('CODE',code)
    (output/'fixture.c').write_text(fixture,encoding='ascii');command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    limit=2**64-1;protections=[1,2,4,8,16,32,64,128,260,514,1028]
    cases=[(base+offset,length,base,4096,state,protect,failed) for base in [4096,2**31,2**64-8192] for offset in [0,1,2048,4095,4096]
           for length in [0,1,2,16,4096,8192,limit] for state in [0,4096,8192,65536] for protect in protections for failed in [0,1]]
    cases.extend((0,length,4096,4096,4096,4,failed) for length in [0,1,limit] for failed in [0,1])
    randomizer=random.Random(20261018)
    for _ in range(4096):
        address=randomizer.randrange(1,2**64);cases.append((address,randomizer.randrange(2**64),address&~4095,4096,randomizer.choice([4096,8192]),randomizer.choice(protections),randomizer.randrange(2)))
    def oracle(address,length,base,size,state,protect,failed):
        calls=int(address!=0)
        if not address or failed or state!=4096 or protect&(1|256) or not(protect&238):return (0,calls)
        end=(address+length)&limit
        return (int(end>=address and end<=((base+size)&limit)),calls)
    inputs=''.join('%d %d %d %d %d %d %d\n'%case for case in cases).encode();(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs);(output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr)
    observed=[tuple(map(int,line.split())) for line in process.stdout.decode().splitlines()]
    failures=[dict(index=i,input=case,expected=oracle(*case),observed=observed[i] if i<len(observed) else None) for i,case in enumerate(cases) if i>=len(observed) or observed[i]!=oracle(*case)]
    sanity_process,sanity=execute([str(output/'fixture.exe'),'--real-pages'],output)
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(console),source_sha256=hashlib.sha256(console.read_bytes()).hexdigest(),seed=20261018,cases=len(cases),passed=len(cases)-len(failures),failures=failures,build=build,result=result,sanity=sanity,
                input_sha256=hashlib.sha256(inputs).hexdigest(),exit=int(bool(failures) or process.returncode!=0 or sanity_process.returncode!=0 or len(observed)!=len(cases)),
                scope='Actual legacy or shared memory code, synthetic VirtualQuery oracle plus real process-local mapped pages; no game process or cross-process permission claims')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='failures'},ensure_ascii=False,indent=2));return record['exit']


if __name__=='__main__':
    raise SystemExit(main())
