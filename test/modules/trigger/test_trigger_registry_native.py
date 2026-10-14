import argparse,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ap=argparse.ArgumentParser();ap.add_argument('output');ap.add_argument('--source',type=pathlib.Path,default=ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c');args=ap.parse_args()
out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
source=args.source.resolve()
prefix=r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static unsigned char* image;
static HMODULE TestModule(LPCSTR s){(void)s;return (HMODULE)image;}
#define GetModuleHandleA TestModule
'''
body=r'''
static unsigned char mapObject[64],head[48],builtin[24];
static int nextId=20000,allocFailure=0,checks=0,failures=0;
static unsigned char tokenData[72*64];
void Plugin_Log(const char* fmt,...){(void)fmt;}
int Var64_ReadStoredContainerRaw(void* container,const char* name,long long* out){(void)container;(void)name;(void)out;return 0;}
int ConsoleCmd_IsReadable(const void* p,size_t n){MEMORY_BASIC_INFORMATION b;if(!p||!VirtualQuery(p,&b,sizeof(b)))return 0;return b.State==MEM_COMMIT&&!(b.Protect&PAGE_NOACCESS)&&n<=(size_t)((char*)b.BaseAddress+b.RegionSize-(char*)p);}
int NativeMemory_IsReadable(const void* p,size_t n){return ConsoleCmd_IsReadable(p,n);}
static void* __fastcall alloc(size_t n){return allocFailure?NULL:calloc(1,n);}
static void __fastcall release(void* p){free(p);}
static void* __fastcall factory(void){unsigned char* p=calloc(1,96);*(void**)p=image+RVA_ALWAYS_VT;return p;}
static void makeString(unsigned char* p,const char* s){size_t n=strlen(s);memset(p,0,32);if(n<=15)memcpy(p,s,n+1);else *(char**)p=_strdup(s);*(size_t*)(p+16)=n;*(size_t*)(p+24)=n<=15?15:n;}
static const char* stringText(unsigned char* p){return *(size_t*)(p+24)<=15?(char*)p:*(char**)p;}
static void* __fastcall addToken(int* id,void* raw,void* unused){int* count=(int*)(image+RVA_DYNAMIC_COUNT);char name[64];size_t n=((size_t*)raw)[1];memcpy(name,*(void**)raw,n);name[n]=0;if(strcmp(name,"always")==0){*id=11247;return id;}for(int i=0;i<*count;i++){if(strcmp(stringText(tokenData+72*i+8),name)==0){*id=*(int*)(tokenData+72*i);return id;}}*id=++nextId;*(int*)(tokenData+72**count)=*id;makeString(tokenData+72**count+8,name);++*count;return id;}
static void* __fastcall reg(void* object,int id,void* entry){unsigned char** link=(unsigned char**)(head+8);while(*link!=head){int k=*(int*)(*link+32);if(k==id){*(void**)(*link+40)=entry;return *link;}link=(unsigned char**)(*link+(id<k?0:16));}unsigned char* n=calloc(1,48);*(void**)n=head;*(void**)(n+8)=head;*(void**)(n+16)=head;*(int*)(n+32)=id;*(void**)(n+40)=entry;*link=n;return n;}
static void* __fastcall pack(void* out,const char* key,void* params,int count){makeString(out,key);return out;}
static void* __fastcall format(void* out,void* ctx,void* packed){makeString(out,stringText(packed));return out;}
static void* __fastcall append(void* out,const char* suffix,size_t n){char text[256];strcpy_s(text,256,stringText(out));strncat_s(text,256,suffix,n);if(*(size_t*)((char*)out+24)>15)free(*(void**)out);makeString(out,text);return out;}
static void thunk(size_t rva,void* fn){unsigned char* p=image+rva;p[0]=0x48;p[1]=0xB8;memcpy(p+2,&fn,8);p[10]=0xFF;p[11]=0xE0;}
static void expect(const char* name,int value){++checks;printf("%s=%s\n",name,value?"PASS":"FAIL");if(!value)++failures;}
static int __fastcall truth(void* self,void* ctx){(void)self;(void)ctx;return 1;}
TRG_BOOL_DEF(unit,"unit_trigger","Native unit trigger","UNIT_TRIGGER_TEXT",truth)
int main(void){
 TriggerDef other;unsigned char instance[96]={0},text[32];void* p;int count;
 image=VirtualAlloc(NULL,0x4000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
 if(!image)return 2;
 *(void**)(image+RVA_TRIGGER_MAP)=mapObject;*(void**)(mapObject+24)=head;head[25]=1;*(void**)(head+8)=head;
 *(void**)(image+RVA_DYNAMIC_TOKENS)=tokenData;
 *(int*)(image+RVA_STATIC_TOKENS)=11247;makeString(image+RVA_STATIC_TOKENS+8,"always");reg(mapObject,11247,builtin);
 *(void**)(image+RVA_ALWAYS_VT+4*8)=image+RVA_ALWAYS_PARSE;*(void**)(image+RVA_ALWAYS_VT+22*8)=image+RVA_ALWAYS_EVAL;
 *(void**)(image+RVA_ALWAYS_ENTRY_VT+8)=image+RVA_ALWAYS_FACTORY;
 thunk(RVA_GAME_ALLOC,alloc);thunk(RVA_GAME_FREE,release);thunk(RVA_ALWAYS_FACTORY,factory);thunk(RVA_ADD_TOKEN,addToken);thunk(RVA_REGISTER_TRIGGER,reg);thunk(RVA_PACK_KEY,pack);thunk(RVA_FORMAT_TEXT,format);thunk(RVA_APPEND_TEXT,append);
 expect("not_ready",!Trigger_RegistryReady());unit_fill();expect("pending",!Trigger_RegistryRegister(&unit_def)&&unit_def.state==TRG_STATE_PENDING);
 image[RVA_LEXER_INIT]=image[RVA_LEXER_SYNC]=1;
 expect("ready",Trigger_RegistryReady());expect("register",Trigger_RegistryRegister(&unit_def)&&unit_def.state==TRG_STATE_OK);
 count=Trigger_RegistryRegisteredCount();expect("idempotent",Trigger_RegistryRegister(&unit_def)&&Trigger_RegistryRegisteredCount()==count);
 expect("entry_flag",*((unsigned char*)unit_def.entry+16)==1);
 expect("instance_factory",(p=unit_factory())!=NULL&&*(void**)p==unit_def.vtStorage+1);free(p);
 instance[88]=1;expect("yes",unit_eval(instance,(void*)1)==1);instance[88]=0;expect("no",unit_eval(instance,(void*)1)==0);
 expect("null_predicate",!Trigger_EvaluateBool(instance,(void*)1,NULL));expect("null_self",!Trigger_EvaluateBool(NULL,(void*)1,truth));
 other=unit_def;other.state=TRG_STATE_PENDING;other.entry=NULL;expect("duplicate",!Trigger_RegistryRegister(&other));
 other=unit_def;other.name="always";other.state=TRG_STATE_PENDING;other.entry=NULL;expect("builtin_collision",!Trigger_RegistryRegister(&other)&&Trigger_FindEntry(mapObject,11247)==builtin);
 {void* saved=*(void**)(head+8);*(void**)(head+8)=head;other.state=TRG_STATE_PENDING;expect("builtin_not_inserted",!Trigger_RegistryRegister(&other));*(void**)(head+8)=saved;}
 expect("invalid_names",!Trigger_ValidName("9bad")&&!Trigger_ValidName("bad-name")&&!Trigger_ValidName("UPPER")&&!Trigger_ValidName("")&&!Trigger_ValidName(NULL));
 expect("valid_name",Trigger_ValidName("_valid_2"));
 other=unit_def;other.name="unit_no_alloc";other.state=TRG_STATE_PENDING;other.entry=NULL;allocFailure=1;expect("allocation_failure",!Trigger_RegistryRegister(&other)&&Trigger_RegistryRegisteredCount()==count);allocFailure=0;
 expect("retry",Trigger_RegistryRegister(&other));expect("null_def",!Trigger_RegistryRegister(NULL));
 expect("empty_batch",!Trigger_RegistryRegisterAll(NULL,3)&&!Trigger_RegistryRegisterAll(NULL,0));
 instance[88]=1;Trigger_BuildTooltip(instance,text,(void*)1,0,"UNIT_TRIGGER_TEXT");expect("tooltip_yes",strcmp(stringText(text),"UNIT_TRIGGER_TEXT = yes\n")==0);if(*(size_t*)(text+24)>15)free(*(void**)text);
 Trigger_BuildTooltip(instance,text,(void*)1,1,"UNIT_TRIGGER_TEXT");expect("tooltip_inversion",strcmp(stringText(text),"UNIT_TRIGGER_TEXT = no\n")==0);if(*(size_t*)(text+24)>15)free(*(void**)text);
 g_scriptFixtureReady=0;expect("binding_ready_gate",!Trigger_RegistryReady());expect("binding_factory_gate",Trigger_NewInstance(image)==NULL);g_scriptFixtureReady=1;
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failures,failures);return failures?1:0;
}
'''
(out/'fixture.c').write_text(prefix+'\n#include \"'+(ROOT/'test/lib/native_script_bindings_fixture.h').as_posix()+'\"\n#define RVA_DYNAMIC_COUNT 0x035E1ACCu\n#define RVA_DYNAMIC_TOKENS 0x035E1AC0u\n'+'\n#include "'+source.as_posix()+'"\n'+body,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
include=(ROOT/'src/plugin/SDK_RVA/console').as_posix()
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC /I"'+include+'" fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True)
result={'command':sys.argv,'stdout':p.stdout.decode('ascii',errors='replace'),'stderr':p.stderr.decode('ascii',errors='replace'),'exit':p.returncode}
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
