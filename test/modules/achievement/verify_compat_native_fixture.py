import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
D = ROOT / "test/reports/20261013_achievement_eligibility"
D.mkdir(parents=True, exist_ok=True)
source = r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
SYMBOL_FIXTURE
#include "SOURCE"
static unsigned char manager[168], console[224], network[16], items[3][96], ironNode[96];
static unsigned char backend[96], steamContext[280], statsInterface[16];
static void* pending[16], *done[16], *excluded[16], *all[3], *networkTable[3], *itemTable[13], *nodeTable[4];
static unsigned short tracked[16];
static int mp, completions, happenedValue, throwNode;
typedef struct { void** table; int value; int iron; } Node;
static Node possibleNodes[2], happenedNodes[2];
static unsigned char __fastcall False(void* p) { (void)p; return 0; }
static unsigned char __fastcall Multiplayer(void* p) { (void)p; return (unsigned char)mp; }
static unsigned char __fastcall IsCompleted(void* p) { return *((unsigned char*)p + 84); }
static unsigned char __fastcall Evaluate(void* p, void* scope) {
    Node* n=(Node*)p; (void)scope;
    if(throwNode) RaiseException(0xE0001234,0,0,NULL);
    if(n==&happenedNodes[0]) return (unsigned char)happenedValue;
    return (unsigned char)(n->value && (!n->iron || Iron(ironNode)));
}
static void __fastcall OriginalRebuild(unsigned char* p, void* s) {
    (void)s; *(int*)(p+52)=*(int*)(p+76)=*(int*)(p+100)=*(int*)(p+148)=0;
}
static void __fastcall OriginalUpdate(unsigned char* p, void* s) { (void)p;(void)s; }
static void __fastcall AddPointer(void* v, const void* value) {
    unsigned char* p=(unsigned char*)v; int n=*(int*)(p+12);
    (*(void***)p)[n]=*(void*const*)value; *(int*)(p+12)=n+1;
}
static void __fastcall AddId(void* v, const void* value) {
    unsigned char* p=(unsigned char*)v; int n=*(int*)(p+12);
    (*(unsigned short**)p)[n]=*(const unsigned short*)value; *(int*)(p+12)=n+1;
}
static __int64 __fastcall Complete(void* p, void* a) {
    unsigned char* m=(unsigned char*)p; int n=*(int*)(m+52),i;
    for(i=0;i<n && pending[i]!=a;++i){}
    if(i>=n) return 0;
    ++completions; *((unsigned char*)a+84)=1; pending[i]=pending[n-1]; tracked[i]=tracked[n-1];
    --*(int*)(m+52);--*(int*)(m+148); AddPointer(m+64,&a); return 1;
}
static void Trampoline(size_t rva, void* fn) {
    unsigned char* p=g_base+rva; p[0]=0x48;p[1]=0xB8;memcpy(p+2,&fn,8);p[10]=0xFF;p[11]=0xE0;
    FlushInstructionCache(GetCurrentProcess(),p,12);
}
void Plugin_Log(const char* f,...) { (void)f; }
int ConsoleCmd_IsReadable(const void* p,size_t n) { return p!=NULL && n<2000000; }
int ConsoleCmd_RegisterAll(const CmdDef* d,int n) {(void)d;return n;}
void ConsoleCmd_InitResult(CmdResult* p){memset(p,0,sizeof(*p));}
void ConsoleCmd_SetMessage(CmdResult* p,const char*s){(void)p;(void)s;}
int InlineHook_Init(void){return 1;}
MH_STATUS WINAPI MH_CreateHook(LPVOID p,LPVOID q,LPVOID* r){(void)p;(void)q;(void)r;return MH_OK;}
MH_STATUS WINAPI MH_QueueEnableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_QueueDisableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_ApplyQueued(void){return MH_OK;}
MH_STATUS WINAPI MH_DisableHook(LPVOID p){(void)p;return MH_OK;}
MH_STATUS WINAPI MH_RemoveHook(LPVOID p){(void)p;return MH_OK;}
int main(void) {
    int passed=0,total=0,i,raised=0;
    struct {void* data;int count;int pad;} scope;
    unsigned char scopeData[32]={0};
    struct {unsigned short* data;int capacity;int count;} ids;
    unsigned short saved=7;
#define CHECK(x) do{++total;if(x)++passed;else printf("FAIL line=%d\n",__LINE__);}while(0)
    g_base=(unsigned char*)VirtualAlloc(NULL,0x3600000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
    if(!g_base)return 3;
    g_installed=1;g_eligible=False;g_iron=False;g_rebuild=OriginalRebuild;g_restore=OriginalRebuild;g_update=OriginalUpdate;
    networkTable[2]=Multiplayer;*(void***)network=networkTable;*(void**)(console+144)=network;
    *(void**)(g_base+0x35E1A80)=console;manager[161]=1;g_base[0x34530D4]=g_base[0x332EC69]=1;
    *(void**)(manager+16)=all;*(int*)(manager+28)=3;
    *(void**)steamContext=g_base+0x2B5BE00;steamContext[266]=1;*(void**)(steamContext+160)=statsInterface;*(void**)(backend+16)=steamContext;
    *(void**)(manager+40)=pending;*(void**)(manager+64)=done;*(void**)(manager+88)=excluded;*(void**)(manager+136)=tracked;
    itemTable[12]=IsCompleted;nodeTable[3]=Evaluate;ironNode[88]=1;
    for(i=0;i<3;++i){all[i]=items[i];*(void***)items[i]=itemTable;*(unsigned short*)(items[i]+80)=(unsigned short)(7+i);*(void**)(items[i]+72)=backend;}
    possibleNodes[0].table=nodeTable;possibleNodes[0].value=1;possibleNodes[0].iron=1;
    possibleNodes[1].table=nodeTable;possibleNodes[1].value=0;
    happenedNodes[0].table=happenedNodes[1].table=nodeTable;happenedNodes[1].value=1;happenedNodes[1].iron=1;
    *(void**)(items[0]+16)=&possibleNodes[0];*(void**)(items[1]+16)=&possibleNodes[1];
    *(void**)(items[0]+24)=&happenedNodes[0];*(void**)(items[1]+24)=&happenedNodes[1];items[2][84]=1;
    Trampoline(0x1205A0,AddPointer);Trampoline(0x61D0D0,AddId);Trampoline(0x61CE50,Complete);
    scope.data=scopeData;scope.count=1;scope.pad=0;
    CHECK(Eligible(manager)==1);mp=1;CHECK(Compatible(manager)==0);CHECK(Eligible(manager)==0);mp=0;
    manager[161]=0;CHECK(Eligible(manager)==1);manager[161]=1;
    steamContext[266]=0;CHECK(Compatible(manager)==0);steamContext[266]=1;
    *(void**)(steamContext+160)=NULL;CHECK(Compatible(manager)==0);*(void**)(steamContext+160)=statsInterface;
    manager[164]=1;CHECK(Compatible(manager)==0);manager[164]=0;
    manager[160]=1;CHECK(Compatible(manager)==0);manager[160]=0;
    manager[163]=1;CHECK(Compatible(manager)==0);manager[163]=0;
    CHECK(Iron(ironNode)==0);CHECK(Possible(items[0],&scope)==1);CHECK(Iron(ironNode)==0);
    g_possible=1;ironNode[88]=0;CHECK(Iron(ironNode)==0);ironNode[88]=1;g_possible=0;
    Rebuild(manager,&scope);CHECK(*(int*)(manager+52)==1);CHECK(*(int*)(manager+76)==1);CHECK(*(int*)(manager+100)==1);CHECK(*(int*)(manager+148)==1);CHECK(tracked[0]==7);
    CHECK(((Eval)nodeTable[3])(&happenedNodes[1],&scope)==0);
    Update(manager,&scope);CHECK(completions==0);happenedValue=1;Update(manager,&scope);CHECK(completions==1);CHECK(*(int*)(manager+52)==0);CHECK(*(int*)(manager+148)==0);
    Update(manager,&scope);CHECK(completions==1);CHECK(manager[162]==0&&manager[163]==0&&g_base[0x34530D4]==1&&g_base[0x332EC69]==1);
    items[0][84]=0;happenedValue=0;ids.data=&saved;ids.capacity=1;ids.count=1;Restore(manager,&ids);CHECK(*(int*)(manager+52)==1&&tracked[0]==7);CHECK(*(int*)(manager+100)==1);
    ids.count=0;Restore(manager,&ids);CHECK(g_needRebuild==1);Update(manager,&scope);CHECK(g_needRebuild==0&&*(int*)(manager+52)==1);
    throwNode=1;__try{Possible(items[0],&scope);}__except(EXCEPTION_EXECUTE_HANDLER){raised=1;}CHECK(raised&&g_possible==0);throwNode=0;
    mp=1;Rebuild(manager,&scope);CHECK(*(int*)(manager+52)==0);mp=0;
    printf("%d/%d production compatibility wrappers with mocked native dependencies; no Steam calls\n",passed,total);
    VirtualFree(g_base,0,MEM_RELEASE);return passed==total?0:1;
}
'''.replace("SOURCE", (ROOT / "src/plugin/SDK_RVA/achievement/achievement_compat.c").as_posix())
source = source.replace("SYMBOL_FIXTURE", '#include "' + (ROOT / "test/lib/native_symbols_fixture.h").as_posix() + '"' if "NativeAdapter_GroupReady" in (ROOT / "src/plugin/SDK_RVA/achievement/achievement_compat.c").read_text(encoding="utf-8") else "")
cpp = D / "compat_fixture.c"
cpp.write_text(source, encoding="utf8")
exe = D / "compat_fixture.exe"
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
cmd = f'"{vc}" >nul && cl /nologo /TC /MT /I"{ROOT / "src/plugin/SDK_RVA/minihook/include"}" "{cpp}" /Fe:"{exe}" /Fo:"{D / "compat_fixture.obj"}"'


def run(command):
    p = subprocess.run(command, capture_output=True)
    return dict(command=command, stdout=p.stdout.decode("utf8", errors="replace"), stderr=p.stderr.decode("utf8", errors="replace"), exit=p.returncode)


build = run('cmd /d /s /c "' + cmd + '"')
result = run([str(exe)]) if build["exit"] == 0 else build
record = dict(build=build, result=result, scope="Actual production wrapper source, controlled native mocks; not real game or Steam integration")
(D / "compat_fixture.json").write_text(json.dumps(record, indent=2), encoding="utf8")
print(json.dumps(record, indent=2))
assert result["exit"] == 0
