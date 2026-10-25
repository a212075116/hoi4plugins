import argparse
import json
import pathlib
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
fixture = r'''
#include <windows.h>
#include <tlhelp32.h>
#include <string>
#include <vector>
#include <algorithm>
#include <new>
#include <cstdlib>
#include <cstdio>
#include <cstring>
static bool failAllocation;
void* operator new(size_t size){if(failAllocation){failAllocation=false;throw std::bad_alloc();}if(void* p=std::malloc(size?size:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete(void* p,size_t)noexcept{std::free(p);}
static int mode,procLive,snapLive,procClose,snapClose,entryReads,tableReads,managerReads,checks,failed;
static unsigned long long trace=1469598103934665603ULL;
static const uintptr_t base=0x10000000,manager=0x20000000,entries=0x30000000,alias=0x40000000,longName=0x50000000;
static unsigned char entryData[912];
struct Table{uintptr_t data;int capacity,count;};
struct RemoteString{unsigned char data[16];uint64_t size,capacity;};
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL mode=%d line=%d\n",mode,__LINE__);}}while(0)
static void event(unsigned long long value){trace=(trace^value)*1099511628211ULL;}
static HANDLE WINAPI FakeOpen(DWORD rights,BOOL inherit,DWORD pid){event(1);CHECK(rights==(PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION)&&!inherit&&pid==1234);if(mode==1)return NULL;procLive=1;return (HANDLE)0x11;}
static HANDLE WINAPI FakeSnapshot(DWORD flags,DWORD pid){event(2);CHECK(flags==(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32)&&pid==1234);if(mode==2)return INVALID_HANDLE_VALUE;snapLive=1;return (HANDLE)0x22;}
static BOOL WINAPI FakeClose(HANDLE h){event(h==(HANDLE)0x11?3:4);if(h==(HANDLE)0x11){CHECK(procLive==1);procLive=0;++procClose;}else{CHECK(h==(HANDLE)0x22&&snapLive==1);snapLive=0;++snapClose;}return TRUE;}
static BOOL WINAPI FakeFirst(HANDLE h,LPMODULEENTRY32W module){event(5);CHECK(h==(HANDLE)0x22&&module->dwSize==sizeof(*module));if(mode==31)throw std::bad_alloc();wcscpy_s(module->szModule,mode==3?L"other.exe":L"hoi4.exe");module->modBaseAddr=(BYTE*)base;return TRUE;}
static BOOL WINAPI FakeNext(HANDLE h,LPMODULEENTRY32W module){event(6);(void)h;(void)module;return FALSE;}
static BOOL WINAPI FakeRead(HANDLE h,LPCVOID pointer,LPVOID out,SIZE_T size,SIZE_T* got){
 uintptr_t address=(uintptr_t)pointer;event(address);event(size);CHECK(h==(HANDLE)0x11&&procLive);*got=size;
 if(address==base){if(mode==4)return FALSE;IMAGE_DOS_HEADER d={};d.e_magic=mode==5?0:IMAGE_DOS_SIGNATURE;d.e_lfanew=mode==6?0:mode==7?5000:256;memcpy(out,&d,size);return TRUE;}
 if(address==base+256){IMAGE_NT_HEADERS64 n={};n.Signature=mode==8?0:IMAGE_NT_SIGNATURE;n.FileHeader.TimeDateStamp=mode==9?0:0x6AA123BB;n.OptionalHeader.SizeOfImage=mode==10?0:0x37EC000;memcpy(out,&n,size);return TRUE;}
 if(address==base+0x35E1A80){++managerReads;if(mode==11)return FALSE;uintptr_t p=mode==27&&managerReads%2==0?manager+16:manager;memcpy(out,&p,size);return TRUE;}
 if(address==manager){++tableReads;if(mode==12)return FALSE;Table t={entries,2,2};if(mode==13)t.count=0;if(mode==14)t.count=9000;if(mode==15)t.capacity=1;if(mode==16)t.capacity=100001;if((mode==23||mode==24&&tableReads==2)&&tableReads%2==0)t.count=1;memcpy(out,&t,size);return TRUE;}
 if(address==entries){++entryReads;if(mode==30)throw std::bad_alloc();if(mode==17||mode==25&&entryReads==1)return FALSE;memcpy(out,entryData,size);return TRUE;}
 if(address>=alias&&address<alias+129){if(mode==26)return FALSE;const char* s=mode==33?"":"set_alias";size_t i=address-alias;*(char*)out=mode==21?'x':i<strlen(s)?s[i]:0;return TRUE;}
 if(address==longName){if(mode==22)return FALSE;memcpy(out,"set_abcdefghijklmnop",size);return TRUE;}
 return FALSE;
}
#define OpenProcess FakeOpen
#define CreateToolhelp32Snapshot FakeSnapshot
#define Module32FirstW FakeFirst
#define Module32NextW FakeNext
#define ReadProcessMemory FakeRead
#define CloseHandle FakeClose
static DWORD FixtureManagerRva(DWORD size,std::string& error){if(mode==9||size!=0x37EC000){error="Unsupported game version; command catalog not read.";return 0;}return 0x35E1A80;}
#include "SOURCE"
static void prepare(){
 memset(entryData,0,sizeof(entryData));RemoteString first={};const char* name=mode==28?"set_abcdefghijk":"set_foo";first.size=strlen(name);first.capacity=15;memcpy(first.data,name,first.size);if(mode==18)first.size=0;if(mode==19)first.data[0]=' ';if(mode==34)first.capacity=1;memcpy(entryData+8,&first,sizeof(first));
 int count=mode==20?4:1;memcpy(entryData+40,&count,4);uintptr_t a=alias;memcpy(entryData+48,&a,8);
 RemoteString second={};second.size=20;second.capacity=64;a=longName;memcpy(second.data,&a,8);memcpy(entryData+456+8,&second,sizeof(second));
}
int main(){
 for(mode=0;mode<35;++mode){
  procLive=snapLive=procClose=snapClose=entryReads=tableReads=managerReads=0;trace=1469598103934665603ULL;prepare();bool threw=false;std::string error="sentinel",prefix=mode==29?"/":"set_";std::vector<std::string> names;
  failAllocation=mode==32;
  try{names=CommandCatalog::Query(1234,prefix,error);}catch(const std::bad_alloc&){threw=true;}failAllocation=false;
  CHECK(threw==(mode==30||mode==31||mode==32));
  if(!threw){
   if(mode==0||mode==24||mode==25||mode==28){CHECK(names.size()==3&&error=="sentinel");CHECK(names[0]==(mode==28?"set_abcdefghijk":"set_abcdefghijklmnop"));CHECK(names[1]==(mode==28?"set_abcdefghijklmnop":"set_alias"));CHECK(names[2]==(mode==28?"set_alias":"set_foo"));}
   else if(mode==29){CHECK(names.size()==5&&error=="sentinel"&&procClose==0&&snapClose==0);}
   else{CHECK(names.empty());CHECK(error==(mode==1?"Cannot read this game's command catalog.":mode>=2&&mode<=10?"Unsupported game version; command catalog not read.":"Command catalog not ready or changed during snapshot; try Tab again."));}
   if(mode==17||mode==23||mode==27)CHECK(entryReads==3);if(mode==24||mode==25)CHECK(entryReads==2);
  }
  CHECK(!procLive&&!snapLive);
  printf("case=%d names=%zu threw=%d process_closed=%d snapshot_closed=%d live=%d/%d attempts=%d trace=%llu error=%s\n",mode,names.size(),threw,procClose,snapClose,procLive,snapLive,entryReads,trace,error.c_str());
 }
 printf("catalog_cases=35 checks=%d failed=%d; fake WinAPI and allocation fault, no game reads\n",checks,failed);return failed?1:0;
}
'''
source = (root / 'src/debug_console/command_catalog.cpp').read_text(encoding='utf-8-sig')
binding = 'ConsoleManagerRva(exe, nt.OptionalHeader.SizeOfImage, error)'
if source.count(binding) != 1:
    raise SystemExit('Expected one binding lookup in Query')
isolated = output / 'catalog.inc'
isolated.write_text(source.replace(binding, 'FixtureManagerRva(nt.OptionalHeader.SizeOfImage, error)'), encoding='ascii')
fixture = fixture.replace('SOURCE', isolated.as_posix())
(output / "fixture.cpp").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /EHsc /std:c++17 /O2 /I"{root / "src/debug_console"}" fixture.cpp /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual Query and Matching; binding lookup stubbed (covered by test_completion_profile.py); fake WinAPI address space and real C++ allocation exception; no process or game memory opened"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
