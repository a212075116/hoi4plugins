"""Compile production operand routing with controlled native container dependencies."""
import pathlib,subprocess,sys,json,hashlib
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=source.read_text(encoding='utf-8-sig')
def fn(name):
    p=s.index(name+'(');start=s.rfind('static ',0,p);a=s.index('{',p);i=a+1;depth=1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[start:i]+'\n'
prefix=r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#define VAR64_FRAC_SCALE 100000LL
#define RVA_VAR_LOOKUP 0
#define VAR64_SUBOBJ_OFF 88u
#define VAR64_PARAM_SECOND 296u
typedef unsigned char* (__fastcall *Var64LookupFn)(void*,void*,void*);
static long long target=1000000,other=950000,operand=250000;
static unsigned lastOffset=0;
static unsigned char* __fastcall lookup(void* d,void* c,void* x){return (unsigned char*)&target;}
static unsigned char* Var64_Image(void){return (unsigned char*)lookup;}
static int Var64_ReadNameOnly(void* s,char* n,unsigned z){strcpy_s(n,z,"target");return 1;}
static int Var64_ReadOperandName(void* s,char* n,unsigned z){strcpy_s(n,z,"operand");return 1;}
static int Var64_ReadOperandNameAt(void* s,unsigned o,char* n,unsigned z){return Var64_ReadOperandName(s,n,z);}
static void* Var64_ContainerAt(void* s,void* c,unsigned o){lastOffset=o;return o==296?&operand:&other;}
static int Var64_ReadStoredIn(void* c,const char* n,long long* v){if(c!=&operand)return 0;*v=*(long long*)c;return 1;}
static int Var64_IsStored64(void* s,void* c,const char* n){return strcmp(n,"target")==0;}
static void* Var64_FindDebt(void* s,void* c,const char* n){return NULL;}
static unsigned char* Var64_ResolveAddressByName(void* s,void* c,const char* n){return (unsigned char*)&other;}
static long long Var64_LoadSplit64(void* s,void* c,const char* n,unsigned char* a,void* x,void* y){return *(long long*)a;}
static int Var64_ReadOperandLiteral(void* s,long long* v){return 0;}
static int Var64_ResolveGameVariableEx(void* s,void* c,long long* v,void* a,char* n,unsigned z,int m){*v=200000;return 1;}
static long long Var64_ReadTrueRaw(void* s,void* c,const char* n,unsigned char* a){return *(long long*)a;}
static int Var64_CalculateRaw(long long a,long long b,int op,long long* v){*v=a*b/100000;return 1;}
static void Var64_WriteTrueRaw(void* s,void* c,const char* n,unsigned char* a,long long v){*(long long*)a=v;}
static void Var64_FormatPartsToText(long long i,long long f,char* b,unsigned z){b[0]=0;}
static void Plugin_Log(const char* f,...){ }
'''
code=fn('Var64_ReadStoredOperandAt') if 'static int Var64_ReadStoredOperandAt(' in s else ''
code+=fn('Var64_TryDebtArithmetic')
main=r'''
int main(void){char self[544]={0};int ctx=1;
 int handled=Var64_TryDebtArithmetic(self,&ctx,2,"multiply");
 printf("ROOT operand=2.5 target_initial=10 result_raw=%lld descriptor_offset=%u handled=%d other_raw=%lld\n",target,lastOffset,handled,other);
 return handled==1&&other==950000&&(target==2000000||target==2500000)?0:1;
}
'''
(out/'fixture.c').write_text(prefix+code+main,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True)
r={'command':sys.argv,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
