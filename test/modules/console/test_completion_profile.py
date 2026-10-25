import argparse
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=pathlib.Path, default=ROOT / 'src/debug_console/command_catalog.cpp')
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
fixture = r'''
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <cstdio>
#include "SOURCE"
static int checks, failed;
static std::wstring exe, profile;
static std::string good;
static const DWORD imageSize=0x37ec000, originalRva=0x35e1a80;
static void check(bool ok,const char* label){++checks;if(!ok){++failed;printf("FAIL %s\n",label);}}
static std::string replace(std::string s,const std::string& from,const std::string& to){size_t p=s.find(from);if(p==std::string::npos)throw std::runtime_error("fixture missing key");s.replace(p,from.size(),to);return s;}
static void write(const std::wstring& path,const std::string& s){std::ofstream f(path,std::ios::binary|std::ios::trunc);f.write(s.data(),s.size());if(!f)throw std::runtime_error("fixture write");}
static FILETIME stamp(const std::wstring& path){WIN32_FILE_ATTRIBUTE_DATA i={};if(!GetFileAttributesExW(path.c_str(),GetFileExInfoStandard,&i))throw std::runtime_error("fixture stat");return i.ftLastWriteTime;}
static void stamp(const std::wstring& path,FILETIME t){HANDLE h=CreateFileW(path.c_str(),FILE_WRITE_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,0,nullptr);if(h==INVALID_HANDLE_VALUE||!SetFileTime(h,nullptr,nullptr,&t))throw std::runtime_error("fixture stamp");CloseHandle(h);}
static void expect(const char* label,const std::string& body,DWORD expected,DWORD size=imageSize){
 FILETIME t=stamp(exe);ULARGE_INTEGER tick={};tick.LowPart=t.dwLowDateTime;tick.HighPart=t.dwHighDateTime;++tick.QuadPart;t.dwLowDateTime=tick.LowPart;t.dwHighDateTime=tick.HighPart;stamp(exe,t);
 write(profile,body);std::string error="sentinel";DWORD actual=0;bool threw=false;
 try{actual=ConsoleManagerRva(exe,size,error);}catch(...){threw=true;}
 check(!threw&&actual==expected&&(expected?error=="sentinel":error!="sentinel"&&!error.empty()),label);
 printf("case=%s expected=%lu actual=%lu threw=%d error=%s\n",label,expected,actual,threw,error.c_str());
}
int wmain(int argc,wchar_t** argv){
 if(argc!=2)return 2;
 std::filesystem::create_directories(L"game/hoi4plugins/bindings");
 exe=std::filesystem::absolute(L"game/hoi4.exe").wstring();write(exe,"fixture-image-one");
 std::ifstream input(argv[1],std::ios::binary);good.assign(std::istreambuf_iterator<char>(input),{});
 std::string firstSha=FileSha256(exe);
 good=replace(good,"image_sha256=7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5","image_sha256="+firstSha);
 profile=std::filesystem::absolute(L"game/hoi4plugins/bindings/"+std::wstring(firstSha.begin(),firstSha.end())+L".symbols").wstring();
 expect("valid",good,originalRva);
 expect("decimal",replace(good,"console.manager=0x35e1a80","console.manager="+std::to_string(originalRva)),originalRva);
 expect("hex-uppercase",replace(good,"console.manager=0x35e1a80","console.manager=0X35E1A80"),originalRva);
 expect("no-final-newline",good.substr(0,good.size()-1),originalRva);
 expect("whitespace",replace(good,"console.manager=0x35e1a80"," console.manager \t= 0x35e1a80\t\r"),originalRva);
 expect("duplicate",good+"approve.console=1\n",0);
 expect("duplicate-other",good+"field.camera.height=0x69c\n",0);
 expect("duplicate-trimmed",good+" approve.console = 1\n",0);
 expect("unknown",good+"unexpected=1\n",0);
 expect("missing",replace(good,"contract=symbols_v2\n",""),0);
 expect("missing-other",replace(good,"field.camera.height=0x69c\n",""),0);
 expect("syntax",good+"invalid-line\n",0);
 expect("empty-key",good+"=value\n",0);
 expect("empty-value",replace(good,"field.camera.height=0x69c","field.camera.height="),0);
 expect("nul",good+std::string(1,'\0'),0);
 expect("high-byte",good+std::string(1,(char)0xff),0);
 expect("control",good+std::string(1,1),0);
 expect("oversize",good+std::string(32769,' '),0);
 expect("empty","",0);
 expect("size-boundary",good+std::string(32768-good.size(),' '),originalRva);
 expect("schema",replace(good,"schema=1","schema=2"),0);
 expect("contract",replace(good,"contract=symbols_v2","contract=symbols_v1"),0);
 expect("identity",replace(good,"image_sha256=","image_sha256=0"),0);
 expect("unapproved",replace(good,"approve.console=1","approve.console=0"),0);
 expect("dependency",replace(good,"approve.core=1","approve.core=0"),0);
 expect("approval-value",replace(good,"approve.diag=1","approve.diag=2"),0);
 for(const char* value:{"0","-1","+1","0x","4294967296","0x100000001","0xffffffffffffffff","0x35e1a80junk","123 4"}){
  std::string label=std::string("number-")+value;expect(label.c_str(),replace(good,"console.manager=0x35e1a80",std::string("console.manager=")+value),0);
 }
 expect("small-image",good,0,7);
 expect("range",good,0,originalRva+7);
 expect("boundary",good,originalRva,originalRva+8);
 expect("wrap",replace(good,"console.manager=0x35e1a80","console.manager=0xfffffffc"),0,MAXDWORD);
 expect("recovery",good,originalRva);
 FILETIME t=stamp(profile);write(profile,replace(good,"console.manager=0x35e1a80","console.manager=0x35e1a88"));stamp(profile,t);
 std::string error;check(ConsoleManagerRva(exe,imageSize,error)==originalRva+8,"same-stamp-rva-edit");
 t=stamp(profile);write(profile,replace(good,"approve.console=1","approve.console=0"));stamp(profile,t);error.clear();check(ConsoleManagerRva(exe,imageSize,error)==0&&!error.empty(),"same-stamp-revocation");
 expect("reapprove",good,originalRva);
 DeleteFileW(profile.c_str());error.clear();check(ConsoleManagerRva(exe,imageSize,error)==0&&!error.empty(),"deleted-profile");
 expect("recreated",good,originalRva);
 write(exe,"fixture-image-with-new-size");error.clear();check(ConsoleManagerRva(exe,imageSize,error)==0&&!error.empty(),"image-size-change");
 std::string sha=FileSha256(exe);good=replace(good,"image_sha256="+firstSha,"image_sha256="+sha);
 profile=std::filesystem::absolute(L"game/hoi4plugins/bindings/"+std::wstring(sha.begin(),sha.end())+L".symbols").wstring();
 expect("new-image-profile",good,originalRva);
 t=stamp(exe);std::wstring next=exe+L".new";write(next,"fixture-image-with-new-sizf");stamp(next,t);
 if(!MoveFileExW(next.c_str(),exe.c_str(),MOVEFILE_REPLACE_EXISTING))throw std::runtime_error("fixture replace image");
 error.clear();check(ConsoleManagerRva(exe,imageSize,error)==0&&!error.empty(),"image-replaced-same-size-time");
 std::string third=FileSha256(exe);good=replace(good,"image_sha256="+sha,"image_sha256="+third);
 profile=std::filesystem::absolute(L"game/hoi4plugins/bindings/"+std::wstring(third.begin(),third.end())+L".symbols").wstring();
 expect("replacement-profile",good,originalRva);
 printf("completion_profile_checks=%d failed=%d; scratch files only, no game process\n",checks,failed);
 return failed?1:0;
}
'''.replace('SOURCE', args.source.resolve().as_posix())
(output / 'fixture.cpp').write_text(fixture, encoding='ascii')
vc = 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /EHsc /std:c++17 /O2 /I"{ROOT / "src/debug_console"}" fixture.cpp /Fe:fixture.exe' + '"'


def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True, timeout=120)
    return dict(command=command, cwd=str(output), exit=p.returncode,
                stdout=p.stdout.decode('utf-8', 'replace'), stderr=p.stderr.decode('utf-8', 'replace'))


build = run(command)
result = run([str(output / 'fixture.exe'), str(ROOT / 'bindings' / ('7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5.symbols'))]) if build['exit'] == 0 else build
(output / 'result.json').write_text(json.dumps(dict(build=build, result=result, scope='Actual catalog loader, BCrypt and scratch files; no game/process memory'), indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(result['exit'])
