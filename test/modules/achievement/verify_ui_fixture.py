import json
import pathlib
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[3]
D = R / "test/reports/20261013_achievement_ui"
phase = sys.argv[1] if len(sys.argv) > 1 else "MODIFIED"
source = r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "SOURCE"
typedef struct {void** table;CmdString name;int visible;int frame;} Widget;
static Widget icon,other,bottom,window;
static void* wt[56], *bt[23], *it[23];
static unsigned char view[1500];
static char text[512];static int oldTooltips;
static const CmdString* __fastcall GetName(void* p){return &((Widget*)p)->name;}
static void* __fastcall Find(void* p,const CmdString* n,unsigned char create){
 const char*s=n->cap>15?n->u.ptr:n->u.buf;(void)create;
 if(p==&window&&n->size==6&&!memcmp(s,"bottom",6))return &bottom;
 if(p==&bottom&&n->size==sizeof(ACH_UI_NAME)-1&&!memcmp(s,ACH_UI_NAME,n->size))return &icon;
 return NULL;
}
static void __fastcall Show(void*p){((Widget*)p)->visible=1;}
static void __fastcall Frame(void*p,unsigned int n){((Widget*)p)->frame=n;}
static void* __fastcall Assign(void*p,const char*s,size_t n){CmdString*v=(CmdString*)p;memcpy(text,s,n);text[n]=0;v->u.ptr=text;v->size=n;v->cap=511;return p;}
static __int64 __fastcall OriginalUpdate(void*p){(void)p;icon.frame=3;icon.visible=0;return 77;}
static unsigned char __fastcall OriginalTooltip(void*p,void*w,CmdString*out){(void)p;(void)w;++oldTooltips;if(out)Assign(out,"original qualification reasons",30);return 1;}
int ConsoleCmd_IsReadable(const void*p,size_t n){return p!=NULL&&n<10000;}
int ConsoleCmd_RegisterAll(const CmdDef*d,int n){(void)d;return n;}
void ConsoleCmd_InitResult(CmdResult*p){memset(p,0,sizeof(*p));}
void ConsoleCmd_SetMessage(CmdResult*p,const char*s){(void)p;(void)s;}
int AchievementCompat_Installed(void){return 1;}
int InlineHook_Init(void){return 1;}
MH_STATUS WINAPI MH_CreateHook(LPVOID p,LPVOID q,LPVOID*r){(void)p;(void)q;(void)r;return MH_OK;}
MH_STATUS WINAPI MH_QueueEnableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_QueueDisableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_ApplyQueued(void){return MH_OK;}
MH_STATUS WINAPI MH_DisableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_RemoveHook(LPVOID p){(void)p;return MH_OK;}
int main(void){
 int i,passed=0,total=0;CmdString out={{0},0,15};void*fn=(void*)Assign;__int64 result;
#define CHECK(x) do{++total;if(x)++passed;else printf("FAIL line=%d\n",__LINE__);}while(0)
 g_uiBase=(unsigned char*)VirtualAlloc(NULL,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);if(!g_uiBase)return 3;
 g_uiBase[0x129CA0]=0x48;g_uiBase[0x129CA1]=0xB8;memcpy(g_uiBase+0x129CA2,&fn,8);g_uiBase[0x129CAA]=0xFF;g_uiBase[0x129CAB]=0xE0;FlushInstructionCache(GetCurrentProcess(),g_uiBase+0x129CA0,12);
 g_frontUpdate=OriginalUpdate;g_frontTooltip=OriginalTooltip;
 window.table=wt;bottom.table=bt;icon.table=other.table=it;
 wt[55]=Find;bt[17]=Find;it[15]=Show;it[22]=Frame;it[21]=GetName;
 icon.name.u.ptr=ACH_UI_NAME;icon.name.size=sizeof(ACH_UI_NAME)-1;icon.name.cap=icon.name.size;
 memcpy(other.name.u.buf,"other_icon",11);other.name.size=10;other.name.cap=15;
 *(void**)(view+1384)=&window;
 result=UPDATE(view);CHECK(result==77);CHECK(icon.frame==1);CHECK(icon.visible==1);
 TOOLTIP(view,&icon,&out);CHECK(out.size==sizeof(ACH_UI_TEXT)-1&&!memcmp(out.u.ptr,ACH_UI_TEXT,out.size));
 printf("frame=%d visible=%d tooltip=%s\n",icon.frame,icon.visible,text);
 TOOLTIP(view,&other,&out);CHECK(!strcmp(text,"original qualification reasons"));CHECK(oldTooltips>=1);
 CHECK(IsIcon(&icon));CHECK(!IsIcon(&other));CHECK(!IsIcon(NULL));
 it[21]=NULL;CHECK(!IsIcon(&icon));it[21]=GetName;
 *(void**)(view+1384)=NULL;CHECK(UPDATE(view)==77);*(void**)(view+1384)=&window;
 for(i=0;i<10000;++i)UPDATE(view);CHECK(icon.frame==1);
 printf("%d/%d UI fixture, production wrappers and mocked native widgets; no actual rendered GUI\n",passed,total);
 VirtualFree(g_uiBase,0,MEM_RELEASE);return passed==total?0:1;
}
'''.replace("SOURCE", (R / "src/plugin/SDK_RVA/achievement/achievement_ui.c").as_posix())
source = source.replace("UPDATE(", "FrontUpdate(" if phase == "MODIFIED" else "OriginalUpdate(").replace("TOOLTIP(", "FrontTooltip(" if phase == "MODIFIED" else "OriginalTooltip(")
p = D / (phase + "_ui_fixture.c")
p.write_text(source, encoding="utf8")
exe = D / (phase + "_ui_fixture.exe")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
cmd = f'"{vc}" >nul && cl /nologo /TC /MT /I"{R / "src/plugin/SDK_RVA/minihook/include"}" "{p}" /Fe:"{exe}" /Fo:"{D / (phase + "_ui_fixture.obj")}"'


def run(command):
    p = subprocess.run(command, capture_output=True)
    return dict(command=command, stdout=p.stdout.decode("utf8", errors="replace"), stderr=p.stderr.decode("utf8", errors="replace"), exit=p.returncode)


build = run('cmd /d /s /c "' + cmd + '"')
result = run([str(exe)]) if build["exit"] == 0 else build
record = dict(phase=phase, build=build, result=result, scope="Native C production UI wrappers with mocked widget/old UI dependencies; not rendered GUI confirmation")
(D / (phase + "_ui_fixture.json")).write_text(json.dumps(record, indent=2), encoding="utf8")
print(json.dumps(record, ensure_ascii=False, indent=2))
assert result["exit"] == (0 if phase == "MODIFIED" else 1)
