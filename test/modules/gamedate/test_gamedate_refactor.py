import json
import pathlib
import subprocess
import sys


root = pathlib.Path(sys.argv[1]).resolve()
output = pathlib.Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
sdk = root / "src/plugin/SDK_RVA"
fixture = r'''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "CONSOLE_HEADER"
static unsigned char* image;
static unsigned char state[2048], effect[512], panel[16];
static const void* denied;
static int uiCalls, installCalls, installFail, logCalls, checks, failures;
static const char* externalBase;
static unsigned long long readTrace=1469598103934665603ULL;
static int readCalls;
static HMODULE MockModule(LPCSTR name){(void)name;return (HMODULE)image;}
#define GetModuleHandleA MockModule
#include "UI_SOURCE"
#include "DATE_SOURCE"
#undef GetModuleHandleA
static int readable(const void* p,size_t n){
 size_t a=(size_t)p;unsigned long long id=6ULL<<32;
 if(image&&a>=(size_t)image&&a<(size_t)image+0x3330000)id=(1ULL<<32)+(a-(size_t)image);
 else if(a>=(size_t)state&&a<(size_t)state+sizeof(state))id=(2ULL<<32)+(a-(size_t)state);
 else if(a>=(size_t)effect&&a<(size_t)effect+sizeof(effect))id=(3ULL<<32)+(a-(size_t)effect);
 else if(a>=(size_t)panel&&a<(size_t)panel+sizeof(panel))id=(4ULL<<32)+(a-(size_t)panel);
 else if(externalBase&&a>=(size_t)externalBase&&a<(size_t)externalBase+64)id=(5ULL<<32)+(a-(size_t)externalBase);
 readTrace=(readTrace^id)*1099511628211ULL;readTrace=(readTrace^n)*1099511628211ULL;++readCalls;
 return p&&n&&p!=denied;
}
int ConsoleCmd_IsReadable(const void* p,size_t n){return readable(p,n);}
int NativeMemory_IsReadable(const void* p,size_t n){return readable(p,n);}
void Plugin_Log(const char* fmt,...){(void)fmt;++logCalls;}
static long long __fastcall OriginalUi(void* p,void* unused){(void)p;(void)unused;++uiCalls;return 77;}
void* InlineHook_Install(void* target,void* detour){
 ++installCalls;if(target!=image+RVA_GD_UI_DATE_UPDATE||detour!=(void*)Hook_UiDateUpdate)return NULL;
 return installFail?NULL:(void*)OriginalUi;
}
int InlineHook_InstallInto(void* target,void* detour,void** original){void* value=InlineHook_Install(target,detour);if(!value)return 0;*original=value;return 1;}
void ConsoleCmd_InitResult(CmdResult* out){memset(out,0,sizeof(*out));}
void ConsoleCmd_SetMessage(CmdResult* out,const char* text){(void)out;(void)text;}
int ConsoleCmd_GetArg(CmdArgs* args,int i,char* dst,size_t n){(void)args;(void)i;(void)dst;(void)n;return 0;}
int ConsoleCmd_RegisterAll(const CmdDef* defs,int n){(void)defs;return n;}
#define CHECK(x) do{++checks;if(!(x)){++failures;printf("FAIL line=%d\n",__LINE__);}}while(0)
static unsigned int seed=0x20261014u;
static unsigned int next(void){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
static const int daysInMonth[12]={31,28,31,30,31,30,31,31,30,31,30,31};
static int oracle(int y,int m,int d,int h){
 long long days=(long long)y*365+d-1;int i;
 for(i=0;i<m-1;++i)days+=daysInMonth[i];
 return (int)(43800000LL+days*24+h);
}
static void fields(int y,int m,int d,int h){
 int yy=0,mm=0,dd=0,hh=0,doy=d,i;
 CHECK(GameDate_GetParts4(&yy,&mm,&dd,&hh));CHECK(yy==y&&mm==m&&dd==d&&hh==h);
 for(i=0;i<m-1;++i)doy+=daysInMonth[i];
 CHECK(*(int*)(state+OFF_GD_YEAR)==y&&*(int*)(state+OFF_GD_MONTH0)==m-1);
 CHECK(*(int*)(state+OFF_GD_DAY)==d&&*(int*)(state+OFF_GD_DOY)==doy);
 CHECK(*(int*)(state+OFF_GD_MONTHDAYS)==daysInMonth[m-1]);
}
int main(void){
 unsigned char* allocated;int i,j,k,y,m,d,h,expected,before,delta,unit,yy,mm,dd,calls;
 char text[64],buffer[80],external[64];const char* invalid[]={NULL,"","1936.2.29","1936.1.0","1936.13.1","0.1.1","10000.1.1","1936.1.1.24"," 1936.1.1","1936.1.1 ","1936/1/1","1936.1.1.x",".1.1","1936..1","1936.1","1936.1.1.1.1"};
 const int sizes[]={0,1,15,16,47,48,64};const int capacities[]={0,15,16,64};const int destinations[]={1,2,8,48,64};
 allocated=(unsigned char*)calloc(1,0x3330000);if(!allocated)return 2;
 image=NULL;CHECK(GameDateUi_Init()==0&&installCalls==0);CHECK(GameDate_GetRaw()==-1);
 image=allocated;*(void**)(image+RVA_GD_GS_GLOBAL)=state;
 installFail=1;CHECK(GameDateUi_Init()==0&&installCalls==1);installFail=0;
 CHECK(GameDateUi_Init()==1&&installCalls==2);CHECK(GameDateUi_Init()==1&&installCalls==2);
 CHECK(!GameDateUi_HasPanel()&&!GameDateUi_Refresh());
 CHECK(Hook_UiDateUpdate(panel,NULL)==77&&GameDateUi_HasPanel());
 calls=logCalls;Hook_UiDateUpdate(panel,NULL);CHECK(logCalls==calls);
 before=uiCalls;CHECK(GameDateUi_Refresh()==1&&uiCalls==before+1);
 denied=panel;before=uiCalls;CHECK(!GameDateUi_Refresh()&&!GameDateUi_HasPanel()&&uiCalls==before);denied=NULL;
 Hook_UiDateUpdate(panel,NULL);Hook_UiDateUpdate(NULL,NULL);CHECK(!GameDateUi_HasPanel());
 Hook_UiDateUpdate(panel,NULL);g_origUiDate=NULL;CHECK(!GameDateUi_Refresh());g_origUiDate=OriginalUi;
 for(i=0;i<20000;++i){
  y=1+(int)(next()%9999);m=1+(int)(next()%12);d=1+(int)(next()%daysInMonth[m-1]);h=(int)(next()%24);
  if(i&1)sprintf_s(text,sizeof(text),"%d.%d.%d.%d",y,m,d,h);
  else{h=0;sprintf_s(text,sizeof(text),"%d.%d.%d",y,m,d);}
  expected=oracle(y,m,d,h);before=uiCalls;
  CHECK(GameDate_EncodeParts(y,m,d,h)==expected);CHECK(GameDate_SetFromText(text));
  CHECK(GameDate_GetRaw()==expected);CHECK(uiCalls==before+1);fields(y,m,d,h);
 }
 for(i=0;i<4000;++i){
  y=1+(int)(next()%9999);m=1+(int)(next()%12);d=1+(int)(next()%daysInMonth[m-1]);h=(int)(next()%24);
  expected=oracle(y,m,d,h);CHECK(GameDate_SetRaw(expected));unit=i%4;delta=(int)(next()%201)-100;
  if(unit==GD_UNIT_MONTH){
   k=y*12+(m-1)+delta;yy=k/12;mm=k%12;if(mm<0){mm+=12;--yy;}++mm;
   if(yy<1)yy=1;if(yy>9999)yy=9999;dd=d>daysInMonth[mm-1]?daysInMonth[mm-1]:d;
   expected=oracle(yy,mm,dd,h);
  }else expected+=delta*(unit==GD_UNIT_YEAR?8760:unit==GD_UNIT_DAY?24:1);
  before=uiCalls;CHECK(GameDate_Add(unit,delta));CHECK(GameDate_GetRaw()==expected&&uiCalls==before+1);
 }
 for(i=0;i<(int)(sizeof(invalid)/sizeof(invalid[0]));++i){
  before=GameDate_GetRaw();calls=uiCalls;CHECK(!GameDate_SetFromText(invalid[i]));CHECK(GameDate_GetRaw()==before&&uiCalls==calls);
 }
 before=GameDate_GetRaw();CHECK(!GameDate_Add(99,1)&&GameDate_GetRaw()==before);
 denied=image+RVA_GD_GS_GLOBAL;CHECK(GameDate_GetRaw()==-1&&!GameDate_SetRaw(123));denied=NULL;
 denied=state+OFF_GD_RAW;CHECK(GameDate_GetRaw()==-1&&!GameDate_SetRaw(123));denied=NULL;
 memset(state+OFF_GD_YEAR,0x5A,32);denied=state+OFF_GD_MONTH0;calls=uiCalls;
 CHECK(GameDate_SetRaw(oracle(1936,1,1,0)));CHECK(*(int*)(state+OFF_GD_YEAR)==0x5A5A5A5A&&uiCalls==calls+1);denied=NULL;
 CHECK(GameDate_SetRaw(-1));CHECK(!GameDate_Add(GD_UNIT_HOUR,1));
 CHECK(GameDate_SetRaw(oracle(1936,1,1,0)));for(i=0;i<16;++i){
  y=m=d=h=0;CHECK(GameDate_DecodeRaw(GameDate_GetRaw(),i&1?NULL:&y,i&2?NULL:&m,i&4?NULL:&d,i&8?NULL:&h));
  CHECK((i&1||y==1936)&&(i&2||m==1)&&(i&4||d==1)&&(i&8||h==0));
 }
 memset(external,'X',sizeof(external));externalBase=external;
 for(i=0;i<7;++i)for(j=0;j<4;++j)for(k=0;k<5;++k){
  NativeString* n=(NativeString*)(effect+OFF_GD_PARAMSTR);int len=sizes[i],valid,count;
  memset(effect,0,sizeof(effect));memset(buffer,0x5A,sizeof(buffer));n->size=len;n->cap=capacities[j];
  if(n->cap<=15)memset(n->u.buf,'X',16);else n->u.ptr=external;
  valid=len>0&&len<48&&destinations[k]>1;
  count=valid?(len<destinations[k]-1?len:destinations[k]-1):0;
  CHECK(GameDate_ReadParamText(effect,buffer,destinations[k])==count);
  if(valid){CHECK(buffer[count]==0);CHECK(buffer[0]=='X');CHECK(!memcmp(buffer,n->cap<=15?n->u.buf:n->u.ptr,count));}
  else CHECK((unsigned char)buffer[0]==0x5A);
  CHECK((unsigned char)buffer[destinations[k]]==0x5A);
 }
 {
  NativeString* n=(NativeString*)(effect+OFF_GD_PARAMSTR);memset(effect,0,sizeof(effect));n->size=16;n->cap=64;n->u.ptr=NULL;
  CHECK(!GameDate_ReadParamText(effect,buffer,48));n->u.ptr=external;denied=external;CHECK(!GameDate_ReadParamText(effect,buffer,48));denied=NULL;
  CHECK(!GameDate_ReadParamText(NULL,buffer,48));CHECK(!GameDate_ReadParamText(effect,NULL,48));
  denied=effect+OFF_GD_PARAMSTR;CHECK(!GameDate_ReadParamText(effect,buffer,48));denied=NULL;
 }
 printf("date=20000 add=4000 param=140 checks=%d failed=%d ui_calls=%d refresh_calls=%d read_calls=%d read_trace=%llu\n",checks,failures,uiCalls,g_uiRefreshCalls,readCalls,readTrace);
 free(allocated);return failures?1:0;
}
'''
for token, path in [("CONSOLE_HEADER", sdk / "console/console_cmd.h"), ("UI_SOURCE", sdk / "gamedate/gamedate_ui.c"), ("DATE_SOURCE", sdk / "gamedate/gamedate.c")]:
    fixture = fixture.replace(token, path.as_posix())
if "NativeAdapter_Symbol" in (sdk / "gamedate/gamedate.h").read_text(encoding="utf-8"):
    fixture = fixture.replace('#include <string.h>\n', '#include <string.h>\n#include "' + (root / "test/lib/native_symbols_fixture.h").as_posix() + '"\n', 1)
(output / "fixture.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
includes = [root / "src/carrier", sdk / "console", sdk / "gamedate", sdk / "hook"]
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT ' + " ".join(f'/I"{p}"' for p in includes) + ' fixture.c /Fe:fixture.exe"'
def run(command):
    process = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=process.stdout.decode("utf-8", errors="replace"), stderr=process.stderr.decode("utf-8", errors="replace"), exit=process.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, oracle_dates=20000, oracle_additions=4000, parameter_matrix=140, scope="Actual date/UI sources with controlled module, memory, UI and command dependencies; no game or rendered GUI"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
sys.exit(result["exit"])
