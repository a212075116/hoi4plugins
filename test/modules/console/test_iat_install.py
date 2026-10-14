import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "effect"))
from test_var64_text_refactor import VCVARS, execute, function

parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--real", action="store_true")
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
source = root / "src/plugin/SDK_RVA/hook/file_redirect.c"
text = source.read_text(encoding="utf-8")
binding = "RedirectIatSlot" in text
fixture = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#define CRASHPATH_MAX 1024
typedef HANDLE (WINAPI *CreateFileWFn)(LPCWSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
typedef HANDLE (WINAPI *CreateFileAFn)(LPCSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
typedef BOOL (WINAPI *CreateDirectoryWFn)(LPCWSTR,LPSECURITY_ATTRIBUTES);
typedef BOOL (WINAPI *CreateDirectoryAFn)(LPCSTR,LPSECURITY_ATTRIBUTES);
static CreateFileWFn g_origCreateFileW;static CreateFileAFn g_origCreateFileA;static CreateDirectoryWFn g_origCreateDirW;static CreateDirectoryAFn g_origCreateDirA;
static volatile LONG g_hookInstalled;
static int g_redirectEnabled=1;
static char g_gameRootPath[CRASHPATH_MAX],g_redirectSourcePrefix[CRASHPATH_MAX];
static void* slots[4];static unsigned missing,failWrite,failRestore,usedWrite,usedRestore,conflict;
static int writes,protects,warnings,checks,failed,activeSlot;static DWORD pageProtection;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL missing=%u write=%u restore=%u line=%d\n",missing,failWrite,failRestore,__LINE__);}}while(0)
static HANDLE WINAPI OriginalW(LPCWSTR a,DWORD b,DWORD c,LPSECURITY_ATTRIBUTES d,DWORD e,DWORD f,HANDLE g){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;return (HANDLE)0x101;}
static HANDLE WINAPI OriginalA(LPCSTR a,DWORD b,DWORD c,LPSECURITY_ATTRIBUTES d,DWORD e,DWORD f,HANDLE g){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;return (HANDLE)0x102;}
static HANDLE WINAPI ForeignW(LPCWSTR a,DWORD b,DWORD c,LPSECURITY_ATTRIBUTES d,DWORD e,DWORD f,HANDLE g){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;return (HANDLE)0x303;}
static BOOL WINAPI OriginalDW(LPCWSTR a,LPSECURITY_ATTRIBUTES b){(void)a;(void)b;return 1;}
static BOOL WINAPI OriginalDA(LPCSTR a,LPSECURITY_ATTRIBUTES b){(void)a;(void)b;return 1;}
static HANDLE WINAPI Hook_CreateFileW(LPCWSTR a,DWORD b,DWORD c,LPSECURITY_ATTRIBUTES d,DWORD e,DWORD f,HANDLE g){return g_origCreateFileW(a,b,c,d,e,f,g);}
static HANDLE WINAPI Hook_CreateFileA(LPCSTR a,DWORD b,DWORD c,LPSECURITY_ATTRIBUTES d,DWORD e,DWORD f,HANDLE g){return g_origCreateFileA(a,b,c,d,e,f,g);}
static BOOL WINAPI Hook_CreateDirectoryW(LPCWSTR a,LPSECURITY_ATTRIBUTES b){return g_origCreateDirW(a,b);}
static BOOL WINAPI Hook_CreateDirectoryA(LPCSTR a,LPSECURITY_ATTRIBUTES b){return g_origCreateDirA(a,b);}
static void* originals[4]={(void*)OriginalW,(void*)OriginalA,(void*)OriginalDW,(void*)OriginalDA};
static void* detours[4]={(void*)Hook_CreateFileW,(void*)Hook_CreateFileA,(void*)Hook_CreateDirectoryW,(void*)Hook_CreateDirectoryA};
static void* published(int i){return i==0?(void*)g_origCreateFileW:i==1?(void*)g_origCreateFileA:i==2?(void*)g_origCreateDirW:(void*)g_origCreateDirA;}
PATH_CODE
static void BuildSourcePrefix(void){strcpy_s(g_redirectSourcePrefix,sizeof(g_redirectSourcePrefix),"C:\\docs\\crashes");}
static DWORD WINAPI Module(HMODULE h,LPSTR out,DWORD n){(void)h;strcpy_s(out,n,"D:\\game\\hoi4.exe");return 16;}
static void** FindIatSlot(const char* dll,const char* name){CHECK(!strcmp(dll,"kernel32.dll"));int i=!strcmp(name,"CreateFileW")?0:!strcmp(name,"CreateFileA")?1:!strcmp(name,"CreateDirectoryW")?2:3;return missing&(1u<<i)?NULL:&slots[i];}
void Plugin_Log(const char* fmt,...){if(strstr(fmt,"protection")||strstr(fmt,"slot"))++warnings;}
static BOOL WINAPI Protect(LPVOID p,SIZE_T n,DWORD protection,PDWORD old){int i=(int)((void**)p-slots);CHECK(i>=0&&i<4&&n==sizeof(void*));++protects;activeSlot=i;*old=pageProtection;
 if(protection==PAGE_READWRITE){CHECK(published(i)&&published(i)!=detours[i]);if((failWrite&(1u<<i))&&!(usedWrite&(1u<<i))){usedWrite|=1u<<i;SetLastError(ERROR_ACCESS_DENIED);return FALSE;}if(conflict&(1u<<i)){slots[i]=(void*)0xF00D;conflict&=~(1u<<i);}}
 else if((failRestore&(1u<<i))&&!(usedRestore&(1u<<i))){usedRestore|=1u<<i;SetLastError(ERROR_ACCESS_DENIED);return FALSE;}
 pageProtection=protection;return TRUE;}
static PVOID WINAPI Exchange(PVOID volatile* p,PVOID value,PVOID expected){void* prior=*p;CHECK(pageProtection==PAGE_READWRITE);if(prior==expected){*p=value;++writes;}return prior;}
#define GetModuleFileNameA Module
#define VirtualProtect Protect
#define InterlockedCompareExchangePointer Exchange
STATE
CODE
static void reset(void){g_hookInstalled=0;g_origCreateFileW=NULL;g_origCreateFileA=NULL;g_origCreateDirW=NULL;g_origCreateDirA=NULL;g_gameRootPath[0]=g_redirectSourcePrefix[0]=0;usedWrite=usedRestore=conflict=0;writes=protects=warnings=0;pageProtection=PAGE_READONLY;for(int i=0;i<4;++i)slots[i]=originals[i];RESET}
static void verify(void){for(int i=0;i<4;++i)if(slots[i]==detours[i]){CHECK(published(i)==originals[i]);if(i==0)CHECK(Hook_CreateFileW(NULL,0,0,NULL,0,0,NULL)==(HANDLE)0x101);if(i==1)CHECK(Hook_CreateFileA(NULL,0,0,NULL,0,0,NULL)==(HANDLE)0x102);}char out[2048];int did;CHECK(RedirectA("C:\\docs\\crashes\\probe\\file.txt",out,sizeof(out),&did)==FileRedirect_Installed());}
int main(void){int cases=0;
 for(missing=0;missing<16;++missing)for(unsigned w=0;w<16;++w)for(unsigned r=0;r<16;++r){
  failWrite=w;failRestore=r;
  reset();int requiredMissing=(missing&5)!=0;int anyFailure=((failWrite|failRestore)&~missing&15)!=0;int first=FileRedirect_Install();CHECK(first==(!requiredMissing&&!anyFailure));CHECK(FileRedirect_Installed()==first);verify();
  if(requiredMissing){CHECK(!writes);}else{
   failWrite=failRestore=0;int second=FileRedirect_Install();CHECK(second==1&&FileRedirect_Installed()==1);for(int i=0;i<4;++i)if(!(missing&(1u<<i)))CHECK(slots[i]==detours[i]);CHECK(pageProtection==PAGE_READONLY);verify();int before=writes;CHECK(FileRedirect_Install()==1&&writes==before);verify();
   slots[0]=(void*)0xF00D;CHECK(FileRedirect_Install()==0&&FileRedirect_Installed()==0&&slots[0]==(void*)0xF00D);verify();slots[0]=originals[0];CHECK(FileRedirect_Install()==1);verify();
  }++cases;
 }
 missing=failWrite=failRestore=0;reset();conflict=1;CHECK(FileRedirect_Install()==0&&slots[0]==(void*)0xF00D);verify();slots[0]=originals[0];CHECK(FileRedirect_Install()==1);verify();++cases;
 originals[0]=(void*)ForeignW;reset();CHECK(FileRedirect_Install()==1&&published(0)==(void*)ForeignW);CHECK(Hook_CreateFileW(NULL,0,0,NULL,0,0,NULL)==(HANDLE)0x303);g_redirectEnabled=0;{char out[2048];int did;CHECK(RedirectA("C:\\docs\\crashes\\probe\\file.txt",out,sizeof(out),&did)==0&&FileRedirect_Installed()==1);}g_redirectEnabled=1;originals[0]=(void*)OriginalW;++cases;
 reset();slots[0]=detours[0];CHECK(FileRedirect_Install()==0&&published(0)==NULL);++cases;
 reset();slots[0]=NULL;CHECK(FileRedirect_Install()==0&&published(0)==NULL);++cases;
 printf("iat_cases=%d checks=%d failed=%d;actual install/slot policy,controlled Win32 protections andIAT discovery,callthrough/retry/foreign/sharedpage protection\n",cases,checks,failed);return failed?1:0;
}
'''
state = ""
reset = ""
if binding:
    start = text.index("typedef struct RedirectIatSlot")
    end = text.index("static unsigned char* FileRedirect_GetModuleBase")
    state = text[start:end]
    reset = "memset(g_redirectSlots,0,sizeof(g_redirectSlots));"
names = ["PatchSlot"] + (["EnsureRedirectSlot", "InstallRedirectSlots"] if binding else []) + ["FileRedirect_Install", "FileRedirect_Installed"]
extract_text = text.replace("int FileRedirect_Install(", "static int FileRedirect_Install(").replace("int FileRedirect_Installed(", "static int FileRedirect_Installed(")
code = "".join(function(extract_text, name) for name in names)
path_code = "".join(function(text, name) for name in ["NormalizeSlashes", "TrimSlash", "StartsWithNoCase", "RedirectA"])
if args.real:
    fixture = fixture[:fixture.index("static BOOL WINAPI Protect(")]
    fixture = fixture.replace("static void* slots[4];", "static void** slots;")
    fixture = fixture.replace("checks,failed,activeSlot;", "activeSlot;static volatile LONG checks,failed;")
    fixture = fixture.replace("++checks;", "InterlockedIncrement(&checks);").replace("++failed;", "InterlockedIncrement(&failed);")
    fixture += r'''
#define GetModuleFileNameA Module
STATE
CODE
static DWORD WINAPI Repeat(LPVOID p){(void)p;for(int i=0;i<64;++i){CHECK(FileRedirect_Install()==1);CHECK(FileRedirect_Installed()==1);CHECK(Hook_CreateFileW(NULL,0,0,NULL,0,0,NULL)==(HANDLE)0x101);}return 0;}
int main(void){DWORD old,before,after;GetProcessHandleCount(GetCurrentProcess(),&before);slots=(void**)VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);CHECK(slots!=NULL);if(!slots)return 2;for(int i=0;i<4;++i)slots[i]=originals[i];CHECK(VirtualProtect(slots,4096,PAGE_READONLY,&old));CHECK(FileRedirect_Install()==1);
 HANDLE threads[32];for(int i=0;i<32;++i){threads[i]=CreateThread(NULL,0,Repeat,NULL,0,NULL);CHECK(threads[i]!=NULL);}for(int i=0;i<32;++i){CHECK(WaitForSingleObject(threads[i],10000)==WAIT_OBJECT_0);CHECK(CloseHandle(threads[i]));}
 for(int i=0;i<4;++i){CHECK(slots[i]==detours[i]);CHECK(published(i)==originals[i]);}MEMORY_BASIC_INFORMATION mbi;CHECK(VirtualQuery(slots,&mbi,sizeof(mbi))!=0&&mbi.Protect==PAGE_READONLY);CHECK(VirtualFree(slots,0,MEM_RELEASE));GetProcessHandleCount(GetCurrentProcess(),&after);CHECK(after==before);printf("real_iat_threads=32 repeat_calls=2048 checks=%ld failed=%ld;actual policy,real readonly shared page/protection/CAS/SRW/callthrough,owned handles restored\n",checks,failed);return failed?1:0;}
'''
fixture = fixture.replace("\nSTATE\n", "\n" + state + "\n").replace("\nCODE\n", "\n" + code + "\n").replace("RESET", reset)
fixture = fixture.replace("PATH_CODE", path_code)
(output / "fixture.c").write_text(fixture, encoding="ascii")
build_process, build = execute('cmd /d /s /c "' + f'"{VCVARS}" >nul && cl /nologo /W3 /TC /MT /O2 fixture.c /Fe:fixture.exe' + '"', output)
if build_process.returncode:
    result = build
else:
    _, result = execute([str(output / "fixture.exe")], output)
record = dict(build=build, result=result, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              input_sha256=hashlib.sha256(b"readonly shared page/32threads*64calls" if args.real else b"missing16*write16*restore16+CASconflict+priorforeign+unboundself+null").hexdigest(),
              scope="Actual installer/policy; imported slot discovery,Win32 protection andcallback bodies controlled; no game native PE traversal claim")
(output / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
