"""Run production tooltip on controlled native formatter/allocator dependencies."""
import ast,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
tree=ast.parse((ROOT/'test/modules/trigger/test_trigger_registry_native.py').read_text())
parts={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and n.targets[0].id in ['prefix','body']}
body=parts['body'].split('int main(void){')[0]
body=body.replace('(void)container;(void)name;(void)out;return 0;','(void)name;if(!container)return 0;*out=*(long long*)container;return 1;')
body=body.replace('static void* __fastcall pack(', 'static void* __fastcall unusedPack(')
extra=r'''
static int ctors=0,dtors=0,tempPresent=0,paramReads=0;
static unsigned __fastcall scopeMask(void* ctx){return *(unsigned*)ctx;}
static void* __fastcall temporary(void){return tempPresent?(void*)1:NULL;}
static void* __fastcall variableName(void* d,void* out,void* ctx,void* index){makeString(out,stringText((unsigned char*)d+112));return out;}
static unsigned char __fastcall contains(void* c,void* view){return strcmp(*(const char**)view,"left")==0;}
static long long* __fastcall param(void* d,long long* out,void* ctx,void* x,unsigned char r){paramReads++;*out=tempPresent&&!((unsigned char*)d)[9]?250000:*(long long*)((char*)d+64);return out;}
static void* __fastcall container(void* d,void* c,int* a,int* b,void** e,void** f,void** g,void** h,void** i,void** j){return *(void**)((char*)d+152);}
static long long* __fastcall half(void* s,long long* out,void* ctx){*out=50000;return out;}
static void __fastcall ctor(void* raw){unsigned char* p=raw;memset(p,0,104);*(size_t*)(p+40)=15;*(size_t*)(p+72)=15;ctors++;}
static void __fastcall dtor(void* raw){unsigned char* p=raw;for(int o=16;o<=48;o+=32)if(*(size_t*)(p+o+24)>15)free(*(void**)(p+o));dtors++;}
static void* __fastcall stringCtor(void* out,const void* text,size_t n){char buf[256];memcpy(buf,text,n);buf[n]=0;makeString(out,buf);return out;}
static void* __fastcall pack(void* out,const char* key,void* values,int count){
 const char* text=key;char buf[512];
 if(!strcmp(key,"PLUGIN_TRIGGER_RESULT_TRUE"))text="TRUE";
 if(!strcmp(key,"PLUGIN_TRIGGER_RESULT_FALSE"))text="FALSE";
 if(!strcmp(key,"PLUGIN_TRIGGER_RESULT_UNAVAILABLE"))text="UNAVAILABLE";
 if(count==4){unsigned char* p=values;for(int i=0;i<4;i++)if(*(int*)(p+i*104)!=1||!*(void**)(p+i*104+8))return NULL;
 sprintf_s(buf,512,"%s: %s %s %s (%s)",key,stringText(p+48),stringText(p+104+48),stringText(p+208+48),stringText(p+312+48));text=buf;}
 makeString(out,text);return out;
}
static void* __fastcall vanillaTooltip(void* self,void* out,void* ctx,unsigned char invert,int indent){makeString(out,"VANILLA LOW-PRECISION LABEL\n");return out;}
static void descriptor(unsigned char* d,const char* name,long long* slot,long long literal){memset(d,0,208);d[8]=1;if(name){makeString(d+112,name);*(void**)(d+152)=slot;}else d[9]=1;*(long long*)(d+64)=literal;}
static void checkTip(TriggerDef* def,unsigned char* self,void* ctx,int invert,const char* expected){unsigned char out[32]={0};Trigger_TypedTooltip(def,self,out,ctx,(unsigned char)invert,0);const char* got=stringText(out);int ok=strcmp(got,expected)==0;checks++;if(!ok)failures++;printf("case=%d got=[%s] expected=[%s] %s\n",checks,got,expected,ok?"PASS":"FAIL");if(*(size_t*)(out+24)>15)free(*(void**)out);}
int main(void){
 unsigned char ctx[176]={0},self[544]={0};long long left=1234567890112500LL;TriggerDef v={0},scalar={0};
 image=VirtualAlloc(NULL,0x4000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);if(!image)return 2;
 thunk(RVA_GAME_FREE,release);thunk(RVA_PACK_KEY,pack);thunk(RVA_FORMAT_TEXT,format);thunk(RVA_APPEND_TEXT,append);
 thunk(0x537d90,scopeMask);thunk(0x544c90,param);thunk(0x542500,container);thunk(0x54f730,temporary);
 thunk(0x5454a0,variableName);thunk(0xbc8d20,contains);thunk(0x29dad0,ctor);thunk(0x29dfe0,dtor);thunk(0x11d970,stringCtor);
 *(void**)(image+RVA_VARIABLE_VT+21*8)=vanillaTooltip;*(void**)(image+RVA_VALUE_VT+21*8)=vanillaTooltip;
 *(unsigned*)ctx=4;v.parameterTemplate=TRG_TEMPLATE_VARIABLE;v.locKey="Variable64";scalar.parameterTemplate=TRG_TEMPLATE_VALUE;scalar.locKey="Half";scalar.valueGetter=half;
 descriptor(self+88,"left",&left,100000);descriptor(self+296,NULL,NULL,1234567890112500LL);*(int*)(self+504)=14580;
 checkTip(&v,self,ctx,0,"Variable64: 12345678901.125 == 12345678901.125 (TRUE)\n");
 checkTip(&v,self,ctx,1,"Variable64: 12345678901.125 != 12345678901.125 (FALSE)\n");
 *(int*)(self+504)=467;checkTip(&v,self,ctx,0,"Variable64: 12345678901.125 > 12345678901.125 (FALSE)\n");
 checkTip(&v,self,ctx,1,"Variable64: 12345678901.125 <= 12345678901.125 (TRUE)\n");
 left=-1;descriptor(self+296,NULL,NULL,-2);checkTip(&v,self,ctx,0,"Variable64: -0.00001 > -0.00002 (TRUE)\n");
 left=(-9223372036854775807LL-1);descriptor(self+296,NULL,NULL,9223372036854775807LL);*(int*)(self+504)=468;
 checkTip(&v,self,ctx,0,"Variable64: -92233720368547.75808 < 92233720368547.75807 (TRUE)\n");
 *(int*)(self+504)=14578;checkTip(&v,self,ctx,1,"Variable64: -92233720368547.75808 == 92233720368547.75807 (FALSE)\n");
 *(int*)(self+504)=14579;checkTip(&v,self,ctx,1,"Variable64: -92233720368547.75808 > 92233720368547.75807 (FALSE)\n");
 *(int*)(self+504)=14581;checkTip(&v,self,ctx,1,"Variable64: -92233720368547.75808 < 92233720368547.75807 (TRUE)\n");
 self[307]=1;int before=paramReads;checkTip(&v,self,ctx,0,"Variable64: ? >= ? (UNAVAILABLE)\n");expect("volatile_tooltip_no_read",paramReads==before);self[307]=0;
 self[304]=0;checkTip(&v,self,ctx,0,"Variable64: ? >= ? (UNAVAILABLE)\n");
 memset(self,0,sizeof(self));descriptor(self+96,NULL,NULL,49999);*(int*)(self+88)=467;
 checkTip(&scalar,self,ctx,0,"Half: 0.5 > 0.49999 (TRUE)\n");checkTip(&scalar,self,ctx,1,"Half: 0.5 <= 0.49999 (FALSE)\n");
 memset(self,0,sizeof(self));left=1234567890112500LL;descriptor(self+88,"left",&left,200000);descriptor(self+296,NULL,NULL,250000);*(int*)(self+504)=14580;tempPresent=1;
 checkTip(&v,self,ctx,0,"Variable64: 2.5 == 2.5 (TRUE)\n");tempPresent=0;
 expect("text_param_lifetime",ctors==dtors&&ctors==56);
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failures,failures);return failures?1:0;
}
'''
(out/'fixture.c').write_text(parts['prefix']+'\n#include "'+source.as_posix()+'"\n'+body+extra,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat';inc=(ROOT/'src/plugin/SDK_RVA/console').as_posix()
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC /I"'+inc+'" fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
# A sibling baseline keeps its original relative include; the current header only adds declarations.
(out/'trigger_reg.h').write_bytes((ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.h').read_bytes())
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);r={'command':sys.argv,'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
