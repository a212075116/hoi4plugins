"""Compile actual console/save string policies and compare fields, aliasing and call order."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'effect'))
from test_var64_text_refactor import VCVARS, execute, function


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source_root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    root=args.source_root.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    console=(root/'src/plugin/SDK_RVA/console/console_cmd.c').read_text(encoding='utf-8-sig')
    variable=(root/'src/plugin/SDK_RVA/variable64/variable64.c').read_text(encoding='utf-8-sig')
    effect=(root/'src/plugin/SDK_RVA/effect/effect_reg.c').read_text(encoding='utf-8-sig')
    code=''.join(function(console,n) for n in ['ConsoleCmd_WriteShortString','ConsoleCmd_WriteString'])
    code+=console[console.index('void ConsoleCmd_SetMessage('):console.index('int ConsoleCmd_GetArg(')]
    code+=function(variable,'Var64_WriteSaveFileName')
    header=root/'src/plugin/SDK_RVA/common/native_string.h'
    if header.exists():selection='static const char* Data(const CmdString* value){return NativeString_Data(value);}\n'
    else:
        cap=effect[effect.index('    cap = *(unsigned long long*)(fin + 0x18);'):effect.index('\n\n    *(unsigned long long*)((unsigned char*)out',effect.index('    cap = *(unsigned long long*)(fin + 0x18);'))]
        selection='static const char* Data(const CmdString* value){unsigned char* fin=(unsigned char*)value;unsigned long long cap;unsigned char* src;\n'+cap+'\nreturn (const char*)src;}\n'
    fixture=r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "CONSOLE_HEADER"
#define EFF_SSO_MAX 15
#define RVA_STR_ASSIGN 0x129CA0u
#define RVA_STRING_ASSIGN 0x129CA0u
typedef void** (__fastcall *AssignFn)(void**,const void*,size_t);
typedef void** (__fastcall *Var64StringAssignFn)(void**,const void*,size_t);
static int flags,moduleCalls,readCalls,assignCalls;static char assigned[576];static size_t assignedLength;
static void** __fastcall Assign(void** dst,const void* src,size_t len){CmdString* field=(CmdString*)dst;++assignCalls;memcpy(assigned,src,len);assigned[len]=0;assignedLength=len;field->u.ptr=assigned;field->size=len;field->cap=len;return dst;}
static HMODULE WINAPI Module(LPCSTR ignored){(void)ignored;++moduleCalls;return flags&1?NULL:(HMODULE)((uintptr_t)Assign-0x129CA0u);}
#define GetModuleHandleA Module
static unsigned char* Var64_Image(void){return (unsigned char*)Module(NULL);}
static int ConsoleCmd_IsReadable(const void* p,size_t n){(void)p;(void)n;++readCalls;return !(flags&2);}
CODE
SELECTION
static void hex(const unsigned char* data,size_t size){size_t i;for(i=0;i<size;++i)printf("%02x",data[i]);}
int main(void){char kind;
 if(sizeof(CmdString)!=32||offsetof(CmdString,size)!=16||offsetof(CmdString,cap)!=24)return 2;
 while(scanf_s(" %c",&kind,1)==1){
  if(kind=='A'){int which,length,alias,ok;unsigned long long capacity;CmdResult result;char payload[576];const char* input;unsigned char normalized[32];
   if(scanf_s("%d %d %llu %d %d",&which,&length,&capacity,&flags,&alias)!=5)return 3;
   memset(&result,0x5a,sizeof(result));result.ok=1;result.message.size=3;result.message.cap=(size_t)capacity;if(capacity>15)result.message.u.ptr=NULL;
   memset(payload,'x',length);payload[length]=0;if(alias==1){memcpy(result.message.u.buf,payload,(size_t)length+1);input=result.message.u.buf;}else if(alias==2)input=(const char*)&result.message.size;else input=payload;
   moduleCalls=readCalls=assignCalls=0;assignedLength=0;assigned[0]=0;
   if(which==0){ConsoleCmd_SetMessage(flags&4?NULL:&result,flags&8?NULL:input);ok=7;}else ok=Var64_WriteSaveFileName(flags&4?NULL:&result.message,flags&8?NULL:input);
   memcpy(normalized,&result.message,sizeof(normalized));if(result.message.cap>15&&result.message.u.ptr==assigned){uint64_t token=2;memcpy(normalized,&token,8);}
   printf("A %d %u %llu %llu %d %d %d %zu ",ok,result.ok,(unsigned long long)result.message.size,(unsigned long long)result.message.cap,moduleCalls,readCalls,assignCalls,assignedLength);hex(normalized,sizeof(normalized));putchar(' ');hex((unsigned char*)assigned,assignedLength);puts("");
  }else if(kind=='D'){unsigned long long size,capacity;int pointerNull;CmdString value;unsigned char before[32];const char* selected;
   if(scanf_s("%llu %llu %d",&size,&capacity,&pointerNull)!=3)return 3;memset(&value,0x5a,sizeof(value));value.size=(size_t)size;value.cap=(size_t)capacity;value.u.ptr=pointerNull?NULL:assigned;memcpy(before,&value,32);selected=Data(&value);
   printf("D %d %d\n",selected==(const char*)&value?1:selected==assigned?2:selected==NULL?0:3,memcmp(before,&value,32)==0);
  }else return 4;
 }
 return 0;
}
'''.replace('CONSOLE_HEADER',(root/'src/plugin/SDK_RVA/console/console_cmd.h').as_posix()).replace('\nCODE\n','\n'+code+'\n').replace('\nSELECTION\n','\n'+selection+'\n')
    (output/'fixture.c').write_text(fixture,encoding='ascii');command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    cases=[f'A {which} {length} {capacity} {flags} 0\n' for which in [0,1] for length in [0,1,14,15,16,31,32,119,120,121,159,160,511]
           for capacity in [0,15,16,127] for flags in range(16)]
    cases+=[f'A {which} {length} {capacity} {flags} 1\n' for which in [0,1] for length in [0,1,14,15] for capacity in [0,15] for flags in range(16)]
    cases+=[f'A {which} 1 {capacity} {flags} 2\n' for which in [0,1] for capacity in [0,15,16,127] for flags in range(16)]
    cases+=[f'D {size} {capacity} {null}\n' for size in [0,1,15,16,33,512,2**64-1] for capacity in [0,14,15,16,127,4095,4096,2**64-1] for null in [0,1]]
    inputs=''.join(cases).encode();(output/'inputs.txt').write_bytes(inputs);process,result=execute([str(output/'fixture.exe')],output,inputs)
    (output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr);assert process.returncode==0 and len(process.stdout.splitlines())==len(cases)
    lines=process.stdout.decode('ascii').splitlines();failures=[]
    for i,case in enumerate(cases):
        fields=case.split()
        if fields[0]=='D':
            capacity=int(fields[2]);null=int(fields[3]);expected=f'D {1 if capacity<=15 else 0 if null else 2} 1'
            if lines[i]!=expected:failures.append(dict(index=i,input=case,expected=expected,observed=lines[i]))
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source_root=str(root),cases=len(cases),selector_oracle_cases=112,failures=failures,build=build,result=result,input_sha256=hashlib.sha256(inputs).hexdigest(),exit=int(bool(failures)),
                scope='Actual console/save helpers and old/current data-selector; raw32-byte field comparison, aliases and native call counters; game assign/image/readability modeled; no game or save I/O')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,ensure_ascii=False,indent=2));return record['exit']


if __name__=='__main__':
    raise SystemExit(main())
