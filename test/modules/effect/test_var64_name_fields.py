"""Compare real name-reader and localization bridge paths with modeled dependencies."""
import argparse
import hashlib
import json
import pathlib
import random

from test_var64_text_refactor import VCVARS, execute, function


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding='utf-8-sig')
    readers = ''.join(function(text, n) for n in ['Var64_ResolveGameVariableEx', 'Var64_ReadNameOnly', 'Var64_ReadOperandNameAt'])
    helper = source.parent/'variable64_name_field.h'
    if helper.exists():
        readers = '#include "'+helper.as_posix()+'"\n'+readers
    language = source.parent/'variable64_language.inc'
    if language.exists():
        language_code = '#include "'+language.as_posix()+'"\n'
    else:
        language_code = text[text.index('#define RVA_VARTEXT_HANDLER'):text.index('EFF_DEF(gamesetvar64,')]
    fixture = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
ADAPTER_FIXTURES
#include "NAME_HEADER"
#include "FORMAT_HEADER"
#define VAR64_SUBOBJ_OFF 88u
#define VAR64_NAME_OFF 200u
#define VAR64_PARAM_SECOND 296u
#define VAR64_PARAM_SELECTOR_A 144u
#define VAR64_PARAM_SELECTOR 160u
#define VAR64_PARAM_TEXT 112u
#define VAR64_PARAM_VALUE 64u
#define VAR64_SSO_LIMIT 15u
#define VAR64_SLOT_SCALE 100000LL
#define VAR64_FRAC_BIAS 100000LL
#define RVA_VAR_LOOKUP 0x542280u
#define RVA_EFF_GETPARAM 0x00544C90u
#define RVA_STRING_APPEND 0x0129C10u
typedef void (__fastcall *Var64GetParamFn)(void*,void*,void*,void*,void*);
typedef void* (__fastcall *Var64LookupFn)(void*,void*,void*);
typedef void** (__fastcall *Var64StringAppendFn)(void**,const void*,size_t);
typedef struct {union {char buf[16];char* ptr;}u;size_t size,cap;} CmdString;
static unsigned char selfBytes[544], savedSelf[544];
static char payload[72], resultBytes[64], trace[512], logText[256], appended[256];
static void* contextTable[8];static void** context=contextTable;
static CmdString outField;
static int flags, mode, metaSeen, sequence, metadataValid, appendCalls, fallbackCalls, hookCalls, hookFails, fallbackValue;
static unsigned long long currentLength;static unsigned char* currentSource;
static long long lowSlot,highSlot,fractionSlot;
static void* __fastcall Original(void* c,const char* t,const char* e,void* o,int d){(void)c;(void)t;(void)e;(void)o;(void)d;++fallbackCalls;return &fallbackValue;}
static void** __fastcall Append(void** dst,const void* src,size_t n){size_t at=strlen(appended);++appendCalls;memcpy(appended+at,src,n);appended[at+n]=0;return dst;}
static unsigned char* Var64_Image(void){return flags&512?NULL:(unsigned char*)((uintptr_t)Append-RVA_STRING_APPEND);}
static HMODULE WINAPI Module(LPCSTR name){(void)name;return (HMODULE)Var64_Image();}
#define GetModuleHandleA Module
static void Plugin_Log(const char* format,...){va_list a;va_start(a,format);vsnprintf(logText,sizeof(logText),format,a);va_end(a);}
static int ConsoleCmd_IsReadable(const void* p,size_t n){
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)selfBytes;int ok=0;char item[80];
 if(a>=b&&a<=b+sizeof(selfBytes)&&n<=b+sizeof(selfBytes)-a)ok=1;
 if(mode==0){
  if(p==selfBytes+200&&n==32&&!metaSeen){metaSeen=1;ok=!(flags&2);}
  else if(p==currentSource){ok=!(flags&4)&&(!(flags&8)||n<=currentLength);}
  if(a>=(uintptr_t)payload && a<=(uintptr_t)payload+sizeof(payload)&&n<=(uintptr_t)payload+sizeof(payload)-a)ok=!(flags&4)&&(!(flags&8)||n<=currentLength);
  if(a>=b&&a<b+sizeof(selfBytes))sprintf_s(item,sizeof(item),"I%llu/%zu:%d;",(unsigned long long)(a-b),n,ok);
  else if(p==currentSource)sprintf_s(item,sizeof(item),"D/%zu:%d;",n,ok);
  else sprintf_s(item,sizeof(item),"X/%zu:%d;",n,ok);
  strcat_s(trace,sizeof(trace),item);
 }else{
  if(p==contextTable)ok=!(flags&1024);
  if(p==&outField)ok=!(flags&2048);
  if(p==(void*)Append)ok=!(flags&4096);
  if(p==(void*)((uintptr_t)Var64_Image()+0x12CF2B0u))ok=!(flags&8192);
 }
 return ok;
}
static void* InlineHook_Install(void* target,void* detour){(void)target;(void)detour;++hookCalls;return hookFails?NULL:(void*)Original;}
int InlineHook_InstallInto(void* target,void* detour,void** original){void* value=InlineHook_Install(target,detour);if(!value)return 0;*original=value;return 1;}
READERS
LANGUAGE
static void __fastcall Resolve(void* ctx,void** out,void* field){
 unsigned char* p=field;size_t size=*(size_t*)(p+16),cap=*(size_t*)(p+24);const char* name=cap<=15?(char*)p:*(char**)p;long long raw;
 int which=strstr(name,"_var64f")?1:strstr(name,"_var64h")?3:2;(void)ctx;
 metadataValid &= size==strlen(name)&&cap==(size<=15?15:size)&&name[size]==0;
 sequence=sequence*10+which;raw=which==1?fractionSlot:which==2?lowSlot:highSlot;
 if((which==1&&(flags&64))||(which==2&&(flags&128))||(which==3&&(flags&256)))++raw;
 *out=(void*)(intptr_t)raw;
}
static void hex(const void* data,size_t size){const unsigned char* p=data;size_t i;for(i=0;i<size;++i)printf("%02x",p[i]);}
static int sanity(void){
 int passed=0,total=0;char text[]="value|2";long long value=0;size_t n;
 mode=1;flags=0;contextTable[4]=(void*)Resolve;lowSlot=100000;highSlot=0;fractionSlot=12500000000LL;
 strcpy_s(appended,sizeof(appended),"prefix:");metadataValid=1;sequence=appendCalls=fallbackCalls=0;g_var64OrigVarTextHandler=Original;
 ++total;passed+=Var64_VarTextBridgeDetour(&context,text,text+strlen(text),&outField,0)==&outField&&!strcmp(appended,"prefix:1.25")&&sequence==123&&appendCalls==1&&fallbackCalls==0&&metadataValid;
 flags=8;sequence=appendCalls=fallbackCalls=0;++total;passed+=Var64_VarTextBridgeDetour(&context,text,text+strlen(text),&outField,1)==&fallbackValue&&fallbackCalls==1&&!sequence&&!appendCalls;
 flags=0;g_var64OrigVarTextHandler=NULL;hookFails=0;hookCalls=0;Var64_InstallLanguageBridge();++total;passed+=hookCalls==1&&g_var64OrigVarTextHandler==Original;
 Var64_InstallLanguageBridge();++total;passed+=hookCalls==1;
 g_var64OrigVarTextHandler=NULL;hookFails=1;Var64_InstallLanguageBridge();++total;passed+=hookCalls==2&&g_var64OrigVarTextHandler==NULL;
 flags=512;Var64_InstallLanguageBridge();++total;passed+=hookCalls==2;
 for(n=1;n<=40;n+=13){char name[48];memset(name,'x',n);name[n]=0;flags=0;sequence=0;metadataValid=1;++total;passed+=Var64_LangResolveSlotValue(&context,name,&value)&&value==1&&metadataValid&&sequence==2;}
 printf("%d/%d field/bridge sanity checks\n",passed,total);return passed!=total;
}
int main(int argc,char** argv){char kind;(void)argv;if(argc>1)return sanity();
 while(scanf_s(" %c",&kind,1)==1){
  if(kind=='N'){
   int which,length,cap,size,nativeMode,ok;long long value=333;unsigned char* address=(unsigned char*)(uintptr_t)99;
   if(scanf_s("%d %d %d %d %d %d",&which,&length,&cap,&size,&flags,&nativeMode)!=6)return 2;
   mode=0;metaSeen=0;currentLength=length;trace[0]=logText[0]=0;memset(selfBytes,0,sizeof(selfBytes));memset(payload,'x',sizeof(payload));payload[length]=0;memset(resultBytes,'Z',sizeof(resultBytes));
   if(cap<=15)memcpy(selfBytes+200,payload,(size_t)length+1);else *(char**)(selfBytes+200)=flags&16?NULL:payload;
   *(unsigned long long*)(selfBytes+216)=length;*(unsigned long long*)(selfBytes+224)=cap;currentSource=cap<=15?selfBytes+200:flags&16?NULL:(unsigned char*)payload;
   if(flags&1)*(void**)(selfBytes+232)=(void*)1;if(flags&32)selfBytes[97]=1;memcpy(savedSelf,selfBytes,sizeof(selfBytes));
   if(which==0)ok=Var64_ResolveGameVariableEx(flags&64?NULL:selfBytes,(void*)1,nativeMode&1?&value:NULL,nativeMode&2?&address:NULL,flags&128?NULL:resultBytes,size,1);
   else if(which==1)ok=Var64_ReadNameOnly(flags&64?NULL:selfBytes,flags&128?NULL:resultBytes,size);
   else ok=Var64_ReadOperandNameAt(flags&64?NULL:selfBytes,88u,flags&128?NULL:resultBytes,size);
   printf("N %d %lld %d %d ",ok,value,address==NULL,memcmp(savedSelf,selfBytes,sizeof(selfBytes))==0);hex(resultBytes,sizeof(resultBytes));printf(" %s ",trace);hex(logText,strlen(logText));puts("");
  }else if(kind=='L'){
   long long integer,fraction;int length,depth;char spec[32],text[128];void* result;
   if(scanf_s("%lld %lld %31s %d %d %d",&integer,&fraction,spec,(unsigned)sizeof(spec),&length,&flags,&depth)!=6)return 2;
   mode=1;lowSlot=(long long)(int)integer*100000;highSlot=(long long)(int)((unsigned long long)integer>>32)*100000;fractionSlot=flags&32?0:(100000+fraction)*100000;
   memset(text,'x',length);text[length]=0;strcat_s(text,sizeof(text),"|");strcat_s(text,sizeof(text),spec);strcpy_s(appended,sizeof(appended),"prefix:");logText[0]=0;sequence=appendCalls=fallbackCalls=0;metadataValid=1;contextTable[4]=(void*)Resolve;g_var64OrigVarTextHandler=flags&1?NULL:Original;
   result=Var64_VarTextBridgeDetour(flags&2?NULL:&context,flags&4?NULL:text,flags&8?text:text+strlen(text),flags&16?NULL:&outField,depth);
   printf("L %d %d %d %d %d ",result==&outField?1:result==&fallbackValue?2:0,sequence,metadataValid,appendCalls,fallbackCalls);hex(appended,strlen(appended));putchar(' ');hex(logText,strlen(logText));puts("");
  }else return 2;
 }
 return 0;
}
'''
    fixture = fixture.replace('NAME_HEADER',(source.parent/'variable64_name.h').as_posix())
    fixture = fixture.replace('FORMAT_HEADER',(source.parent/'variable64_text_format.h').as_posix())
    lib = source.parents[3].parent/'test/lib'
    fixture = fixture.replace('ADAPTER_FIXTURES', '#include "'+(lib/'native_script_bindings_fixture.h').as_posix()+'"\n#include "'+(lib/'native_symbols_fixture.h').as_posix()+'"' if (lib/'native_symbols_fixture.h').exists() else '')
    fixture = fixture.replace('READERS',readers).replace('LANGUAGE',language_code)
    (output/'fixture.c').write_text(fixture,encoding='ascii')
    command = f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build = execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8')
        print(json.dumps(build,indent=2))
        return build_process.returncode
    cases = [f'N {which} {length} {cap} {size} {flag} {native}\n'
             for which in [0,1,2] for length in [0,1,15,16,31,32,33,34,40,41]
             for cap in [15,16,127] for size in [0,7,8,39,40,41,64]
             for flag in [0,1,2,4,8,16,32,64,128,512] for native in [0,1,2,3]]
    cases += [f'L {integer} {fraction} {spec} {length} {flag} {depth}\n'
              for integer,fraction in [(0,0),(1,25000),(-1,-25000),(92233720368547,75807)]
              for spec in ['.','2','+','=*2','%2-'] for length in [1,15,16,33,34,40,41]
              for flag in [0,1,2,4,8,16,32,64,128,256,512,1024,2048,4096] for depth in [0,1]]
    randomizer=random.Random(20261014)
    for _ in range(2048):
        cases.append(f'N {randomizer.randrange(3)} {randomizer.randrange(42)} {randomizer.choice([15,16,127])} {randomizer.choice([7,8,39,40,41,64])} {randomizer.randrange(256)} {randomizer.randrange(4)}\n')
    inputs=''.join(cases).encode('ascii');(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs)
    (output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr)
    sanity_process,sanity=execute([str(output/'fixture.exe'),'--sanity'],output)
    assert process.returncode==0 and len(process.stdout.splitlines())==len(cases)
    (output/'sanity.json').write_text(json.dumps(sanity,indent=2),encoding='utf-8')
    assert sanity_process.returncode==0
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),seed=20261014,cases=len(cases),
                input_sha256=hashlib.sha256(inputs).hexdigest(),build=build,result=result,sanity=sanity,
                scope='Actual reader/bridge/append/install code; modeled readable regions, image/native calls and hook installer; traces/output preserved; no game process or GUI')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    raise SystemExit(main())
