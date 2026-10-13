import pathlib,subprocess,sys,json
from test_var64_text_refactor import function
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=source.read_text(encoding='utf-8-sig')
name_header=source.parent/'variable64_name.h'
if name_header.exists():
    s=s.replace('#include "variable64_name.h"',name_header.read_text(encoding='utf-8-sig'))
def fn(name):
    start=s.rfind('static ',0,s.index(name+'('))
    pos=s.index('{',start);depth=1;i=pos+1
    while depth:
        if s[i]=='{':depth+=1
        elif s[i]=='}':depth-=1
        i+=1
    return s[start:i]+'\n'
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#define VAR64_HIGH_SUFFIX "_var64h"
#define VAR64_FRAC_SUFFIX "_var64f"
#define VAR64_NAME_LIMIT 40u
#define VAR64_SLOT_SCALE 100000LL
#define VAR64_FRAC_SCALE 100000LL
#define VAR64_FRAC_BIAS 100000LL
#define VAR64_KNOWN_NAME_LIMIT 128
#define VAR64_KNOWN_NAME_BYTES 32
static char g_var64KnownNames[128][32];static int g_var64KnownNameCount=0;
static void Plugin_Log(const char* f,...){ }
static int ConsoleCmd_IsReadable(const void* p,size_t n){return p!=NULL;}
static void* Var64_Container(void* self,void* ctx){return ctx;}
typedef struct {unsigned char b[48];} Scope;
static void init(Scope* s){memset(s,0,sizeof(*s));*(void**)(s->b+24)=calloc(512,48);*(int*)(s->b+36)=255;}
'''
math_header=source.parent/'variable64_math.h'
math_include=('#include "'+math_header.as_posix()+'"\n') if math_header.exists() else ''
code=math_include+(fn('Var64_MakePartName') if 'static int Var64_MakePartName(' in s else '')+''.join(fn(n) for n in ['Var64_Fnv1a','Var64_LookupInScope','Var64_MakeHighPartName','Var64_MakeFracPartName','Var64_IsSixtyFourBitName','Var64_RememberSixtyFourBitNameSrc'])
if 'static int Var64_IsStored64(' in s:
    if 'static int Var64_ReadStoredIn(' in s:
        code+=fn('Var64_ReadStoredIn')
    # Select the definition, not its forward declaration.
    code+=function(s,'Var64_IsStored64')
else:code+='static int Var64_IsStored64(void* self,void* ctx,const char* name){return Var64_IsSixtyFourBitName(name);}\n'
main=r'''
static void add(Scope* s,const char* name,long long raw){
 unsigned h=Var64_Fnv1a(name),d=1;unsigned char* p=*(unsigned char**)(s->b+24)+(h&255)*48;
 while(p[4]){p+=48;d++;}
 *(unsigned*)p=h;p[4]=(unsigned char)d;
 if(strlen(name)<=15){memcpy(p+8,name,strlen(name)+1);*(unsigned long long*)(p+32)=15;}
 else{*(char**)(p+8)=_strdup(name);*(unsigned long long*)(p+32)=strlen(name);}
 *(unsigned long long*)(p+24)=strlen(name);*(long long*)(p+40)=raw;
}
static void triple(Scope* s,const char* name,long long low,long long frac){char h[48],f[48];sprintf_s(h,48,"%s_var64h",name);sprintf_s(f,48,"%s_var64f",name);add(s,name,low);add(s,h,0);add(s,f,frac);}
static int failures=0;
static void check(const char* label,int got,int want){printf("%s got=%d expected=%d\n",label,got,want);if(got!=want)failures++;}
int main(void){
 Scope a,b,c,neg,fake,longname,hash;char candidate[16];int i;long long value=0;
 init(&a);init(&b);init(&c);init(&neg);init(&fake);init(&longname);init(&hash);
 triple(&a,"shared",1000000,15000000000LL);
 check("post_load",Var64_IsStored64((void*)1,&a,"shared"),1);
 Var64_RememberSixtyFourBitNameSrc("shared",1);add(&b,"shared",750000);
 check("other_scope",Var64_IsStored64((void*)1,&b,"shared"),0);
 add(&c,"shared_var64h",0);add(&c,"shared_var64f",15000000000LL);
 check("missing_main",Var64_IsStored64((void*)1,&c,"shared"),0);
 triple(&neg,"negative",-100000,5000000000LL);
 check("negative_fraction",Var64_IsStored64((void*)1,&neg,"negative"),1);
 triple(&fake,"fake",750000,150000);
 check("fake_marker",Var64_IsStored64((void*)1,&fake,"fake"),0);
 triple(&longname,"abcdefghijklmnopqrstuvwxyz012345",1234500000,11250000000LL);
 Var64_RememberSixtyFourBitNameSrc("abcdefghijklmnopqrstuvwxyz012345",1);
 check("name32",Var64_IsStored64((void*)1,&longname,"abcdefghijklmnopqrstuvwxyz012345"),1);
 for(i=0;i<100000;i++){sprintf_s(candidate,16,"col%d",i);if((Var64_Fnv1a(candidate)&255)==(Var64_Fnv1a("target")&255))break;}
 add(&hash,candidate,1);add(&hash,"target",12300000);
 check("robin_hood",Var64_LookupInScope(&hash,"target",&value)&&value==12300000,1);
 {void* p=*(void**)(a.b+24);void* copy=malloc(512*48);memcpy(copy,p,512*48);Var64_IsStored64((void*)1,&a,"not_defined");check("no_mutation",memcmp(copy,p,512*48)==0,1);free(copy);}
 printf("checks=8 passed=%d failed=%d\n",8-failures,failures);return failures?1:0;
}
'''
(out/'fixture.c').write_text(prefix+code+main,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
result={'command':sys.argv,'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode}
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
