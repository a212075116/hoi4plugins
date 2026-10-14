import argparse
import ast
import json
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
text = (root / "src/debug_console/main.cpp").read_text(encoding="utf-8")
start = text.index("struct Tail {")
end = text.index("\n};", start) + 3
tail = text[start:end]
tree = ast.parse((ROOT / "test/modules/console/test_catalog_handles.py").read_text(encoding="utf-8"))
catalog_fixture = next(ast.literal_eval(n.value.func.value if isinstance(n.value, ast.Call) else n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "fixture")
allocator = catalog_fixture[catalog_fixture.index("static bool failAllocation;"):catalog_fixture.index("static int mode,")]
header = root / "src/debug_console/owned_kernel_handle.h"
prefix = r'''
#include <windows.h>
#include <string>
#include <vector>
#include <cstdint>
#include <new>
#include <cstdlib>
#include <cstdio>
#include <cstring>
'''
prefix += allocator
prefix += r'''
static char content[200000];static size_t length,position;static DWORD fileId=1,volumeId=2;
static int mode,live,closed,checks,failed;static unsigned long long trace;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL line=%d mode=%d\n",__LINE__,mode);}}while(0)
static void event(unsigned long long value){trace=(trace^value)*1099511628211ULL;}
static HANDLE WINAPI FakeCreate(LPCWSTR path,DWORD access,DWORD share,LPSECURITY_ATTRIBUTES security,DWORD disposition,DWORD attributes,HANDLE parent){
 event(1);CHECK(!wcscmp(path,L"fixture.log")&&access==GENERIC_READ&&share==(FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE)&&!security&&disposition==OPEN_EXISTING&&attributes==FILE_ATTRIBUTE_NORMAL&&!parent);if(mode==1)return INVALID_HANDLE_VALUE;live=1;position=0;return (HANDLE)0x33;
}
static BOOL WINAPI FakeClose(HANDLE h){event(2);CHECK(h==(HANDLE)0x33&&live);live=0;++closed;return TRUE;}
static BOOL WINAPI FakeInfo(HANDLE h,LPBY_HANDLE_FILE_INFORMATION info){event(3);CHECK(h==(HANDLE)0x33&&live);if(mode==8)throw std::bad_alloc();if(mode==2)return FALSE;memset(info,0,sizeof(*info));info->nFileIndexLow=fileId;info->dwVolumeSerialNumber=volumeId;return TRUE;}
static BOOL WINAPI FakeSize(HANDLE h,PLARGE_INTEGER size){event(4);CHECK(h==(HANDLE)0x33&&live);if(mode==3)return FALSE;size->QuadPart=length;return TRUE;}
static BOOL WINAPI FakeSeek(HANDLE h,LARGE_INTEGER offset,PLARGE_INTEGER result,DWORD method){event(5);event(offset.QuadPart);CHECK(h==(HANDLE)0x33&&live&&method==FILE_BEGIN&&!result);if(mode==4)return FALSE;position=(size_t)offset.QuadPart;return TRUE;}
static BOOL WINAPI FakeRead(HANDLE h,LPVOID buffer,DWORD size,LPDWORD got,LPOVERLAPPED overlap){event(6);event(size);CHECK(h==(HANDLE)0x33&&live&&!overlap);if(mode==9)throw std::bad_alloc();if(mode==5)return FALSE;*got=(DWORD)(position<length?length-position:0);if(*got>size)*got=size;memcpy(buffer,content+position,*got);position+=*got;return TRUE;}
static BOOL WINAPI FakeAttributes(LPCWSTR path,GET_FILEEX_INFO_LEVELS level,LPVOID data){event(7);CHECK(!wcscmp(path,L"fixture.log")&&level==GetFileExInfoStandard);auto* info=(WIN32_FILE_ATTRIBUTE_DATA*)data;memset(info,0,sizeof(*info));info->nFileSizeLow=(DWORD)length;return TRUE;}
#define CreateFileW FakeCreate
#define CloseHandle FakeClose
#define GetFileInformationByHandle FakeInfo
#define GetFileSizeEx FakeSize
#define SetFilePointerEx FakeSeek
#define ReadFile FakeRead
#define GetFileAttributesExW FakeAttributes
'''
if header.exists():
    prefix += f'#include "{header.as_posix()}"\n'
main = r'''
static void set(const char* data,size_t n){memcpy(content,data,n);length=n;}
static void append(const char* data,size_t n){memcpy(content+length,data,n);length+=n;}
static unsigned long long hash(const std::string& value){unsigned long long h=1469598103934665603ULL;for(unsigned char c:value)h=(h^c)*1099511628211ULL;return h;}
static std::vector<std::string> poll(Tail& t,const char* label,int fault=0,bool allocation=false){
 mode=fault;closed=0;trace=1469598103934665603ULL;bool threw=false;std::vector<std::string> rows;failAllocation=allocation;
 try{rows=t.Poll();}catch(const std::bad_alloc&){threw=true;}failAllocation=false;
 CHECK(threw==(fault==8||fault==9||allocation));CHECK(!live);
 printf("case=%s rows=%zu offset=%llu id=%llu volume=%lu partial=%zu/%llu sentinel=%zu/%llu dropping=%d closed=%d live=%d threw=%d trace=%llu\n",label,rows.size(),t.offset,t.identity,t.volume,t.partial.size(),hash(t.partial),t.sentinel.size(),hash(t.sentinel),t.dropping,closed,live,threw,trace);
 for(size_t i=0;i<rows.size();++i)printf("row=%s:%zu:%zu:%llu\n",label,i,rows[i].size(),hash(rows[i]));
 live=0;return rows;
}
int main(){
 Tail t;t.path=L"fixture.log";set("",0);
 CHECK(poll(t,"missing",1).empty());CHECK(poll(t,"info-fail",2).empty());CHECK(poll(t,"size-fail",3).empty());CHECK(poll(t,"seek-fail",4).empty());CHECK(t.identity==1);CHECK(poll(t,"read-fail",5).empty());
 set("one\r\ntwo\npart",13);auto rows=poll(t,"initial");CHECK(rows==std::vector<std::string>({"one","two"})&&t.partial=="part"&&t.offset==13);
 append("ial\n",4);CHECK(poll(t,"append")==std::vector<std::string>{"partial"});CHECK(poll(t,"idle").empty());
 ++fileId;set("new\n",4);CHECK(poll(t,"replace")==std::vector<std::string>({"[log reset/recreated]","new"}));
 set("x\n",2);CHECK(poll(t,"truncate")==std::vector<std::string>({"[log reset/recreated]","x"}));
 set("BBBBBB\nMore\n",12);CHECK(poll(t,"regrow")==std::vector<std::string>({"[log reset/recreated]","BBBBBB","More"}));
 ++volumeId;set("v\n",2);CHECK(poll(t,"volume")==std::vector<std::string>({"[log reset/recreated]","v"}));
 ++fileId;set("\xE4\xB8",2);rows=poll(t,"utf8-start");CHECK(rows==std::vector<std::string>{"[log reset/recreated]"});append("\xAD\n",2);CHECK(poll(t,"utf8-end")==std::vector<std::string>{"\xE4\xB8\xAD"});
 ++fileId;memset(content,'A',65535);memcpy(content+65535,"\xE4\xB8\xAD\n",4);length=65539;rows=poll(t,"long-first");CHECK(rows.size()==2&&rows[1].size()==65535+17&&t.partial=="\xE4");rows=poll(t,"long-end");CHECK(rows==std::vector<std::string>{"\xE4\xB8\xAD"});
 ++fileId;for(int i=0;i<300;++i)memcpy(content+2*i,"x\n",2);length=600;rows=poll(t,"batch-first");CHECK(rows.size()==256&&t.offset==510);rows=poll(t,"batch-second");CHECK(rows.size()==45&&t.offset==600);
 Tail a;a.path=L"fixture.log";memset(content,'A',100);length=100;poll(a,"allocation",0,true);
 Tail b;b.path=L"fixture.log";poll(b,"info-throw",8);
 Tail c;c.path=L"fixture.log";poll(c,"read-throw",9);
 printf("tail_polls=21 checks=%d failed=%d;fake file APIs and allocation fault,no game\n",checks,failed);return failed?1:0;
}
'''
(output / "fixture.cpp").write_text(prefix + tail + "\n" + main, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /EHsc /std:c++17 /O2 fixture.cpp /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual Tail extraction;fake file APIs,real C++ allocation exception;state hashes include partial/sentinel;no real logs or game"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
