"""Compile actual setter routing with scoped debt state and controlled native writes."""
import pathlib,re,subprocess,sys,json
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
src=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True);s=src.read_text(encoding='utf-8-sig')
def fn(name):
 for m in re.finditer(r'(?m)^static[^\n]*\b'+name+r'\(',s):
  p=m.start();a=s.index('{',p);semi=s.find(';',p)
  if semi>=0 and semi<a:continue
  i=a+1;depth=1
  while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
  return s[p:i]+'\n'
 raise ValueError(name)
end=s.index('} Var64DebtRecord;')+len('} Var64DebtRecord;');start=s.rfind('typedef struct',0,end)
record=s[start:end]
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define VAR64_FRAC_SCALE 100000LL
#define VAR64_MARK_OFF 505
#define VAR64_MARK_SET 1
#define VAR64_MARK_ADD 2
#define VAR64_MARK_LOG 3
#define VAR64_MARK_MOD 4
#define VAR64_MARK_RND 5
#define VAR64_MARK_CLP 6
#define VAR64_MARK_CLH 7
static long long values[2]={0},delta=1234567890112500LL;
static int wide[2]={0},resolveOk=1;
static int slot(void* ctx){return ctx==(void*)1?0:1;}
static void* Var64_Container(void* self,void* ctx){return ctx;}
static int ConsoleCmd_IsReadable(const void* p,size_t n){return p!=NULL;}
static int Var64_ReadNameOnly(void* self,char* out,unsigned cap){strcpy_s(out,cap,"same");return 1;}
static int Var64_IsStored64(void* self,void* ctx,const char* n){return wide[slot(ctx)];}
static long long Var64_LoadSplit64(void* self,void* ctx,const char* n,unsigned char* addr,void* a,void* b){return *(long long*)addr;}
static int Var64_ResolveGameVariable(void* self,void* ctx,long long* out,unsigned char** addr,char* name,unsigned cap){if(!resolveOk)return 0;*out=delta;*addr=(unsigned char*)&values[slot(ctx)];strcpy_s(name,cap,"same");return 1;}
static void Var64_StoreSplit64(void* self,void* ctx,const char* n,unsigned char* addr,long long raw){*(long long*)addr=raw;wide[slot(ctx)]=1;}
static void Var64_RememberSixtyFourBitNameSrc(const char* n,int source){}
static void Var64_FormatPartsToText(long long a,long long b,char* text,int n){text[0]=0;}
static void Plugin_Log(const char* f,...){}
static void Var64_ClearHighPartAfterVanillaSet(void* self,void* ctx){wide[slot(ctx)]=0;}
static long long __fastcall dummy(void* s,void* c){return 0;}
#define Var64_DoAddToVariable64 dummy
#define Var64_DoLogVariable64 dummy
#define Var64_DoModuloVariable64 dummy
#define Var64_DoRoundVariable64 dummy
#define Var64_DoClampVariable64 dummy
#define Var64_DoClampHighVariable64 dummy
static long long __fastcall nativeSet(void* s,void* c){values[slot(c)]=250000;return 0;}
static long long (__fastcall *g_var64OrigGameSetExec)(void*,void*)=nativeSet;
'''
code=record+'\nstatic Var64DebtRecord records[2];static Var64DebtRecord* g_var64Debts=records;static int g_var64DebtCapacity=2;\n'
code+=fn('Var64_FindDebt')+fn('Var64_ClearDebt')
if 'static void Var64_ResetDebtForSet(' in s:code+=fn('Var64_ResetDebtForSet')
code+=fn('Var64_ReadTrueRaw')+fn('Var64_DoSetVariable64')+fn('Var64_GameSyntaxDetour')
main=r'''
static int checks=0,failed=0;
static void check(const char* key,int ok){checks++;if(!ok)failed++;printf("%s %s\n",key,ok?"PASS":"FAIL");}
static void setup(void){memset(records,0,sizeof(records));for(int i=0;i<2;i++){strcpy_s(records[i].name,40,"same");records[i].container=(void*)(size_t)(i+1);records[i].active=1;records[i].debtInt=3000000000LL;}wide[0]=wide[1]=0;values[0]=values[1]=214748364799999LL;}
int main(void){unsigned char self[544]={0};long long value;
 setup();Var64_GameSyntaxDetour(self,(void*)1);value=Var64_ReadTrueRaw(self,(void*)1,"same",(unsigned char*)&values[0]);printf("native_reset effective_raw=%lld debt_active=%d\n",value,records[0].active);check("native_value",value==250000);check("native_debt_clear",!records[0].active);check("other_scope_preserved",records[1].active&&records[1].debtInt==3000000000LL);
 setup();*(unsigned*)(self+505)=VAR64_MARK_SET;Var64_GameSyntaxDetour(self,(void*)1);check("wide_identity",wide[0]);check("wide_value",values[0]==delta);check("wide_debt_clear",!records[0].active);
 *(unsigned*)(self+505)=0;Var64_GameSyntaxDetour(self,(void*)1);value=Var64_ReadTrueRaw(self,(void*)1,"same",(unsigned char*)&values[0]);printf("demote effective_raw=%lld debt_active=%d\n",value,records[0].active);check("demote_value",value==250000);check("demote_identity",!wide[0]);
 setup();resolveOk=0;*(unsigned*)(self+505)=VAR64_MARK_SET;Var64_GameSyntaxDetour(self,(void*)1);check("failed_set_preserves",records[0].active&&values[0]==214748364799999LL&&!wide[0]);
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+code+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);r={'command':sys.argv,'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode};(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
