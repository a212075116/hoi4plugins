import json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2];D=R/'test/reports/20261012_variable64_transaction/console_permission'
cpp=r'''
#include <windows.h>
#include <cstdio>
#include <vector>
int main(){
 DWORD parentPid=0;GetWindowThreadProcessId(GetShellWindow(),&parentPid);
 HANDLE parent=OpenProcess(PROCESS_CREATE_PROCESS,FALSE,parentPid);if(!parent)return 2;
 SIZE_T n=0;InitializeProcThreadAttributeList(NULL,1,0,&n);std::vector<char> b(n);
 STARTUPINFOEXW si={};si.StartupInfo.cb=sizeof(si);si.lpAttributeList=(LPPROC_THREAD_ATTRIBUTE_LIST)b.data();
 if(!InitializeProcThreadAttributeList(si.lpAttributeList,1,0,&n)||!UpdateProcThreadAttribute(si.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,&parent,sizeof(parent),NULL,NULL))return 2;
 wchar_t command[]=L"\"ROOT/hoi4.exe\" -gdpr-compliant -nolauncher -continuelastsave -plugin-console";
 PROCESS_INFORMATION pi={};BOOL ok=CreateProcessW(L"ROOT/hoi4.exe",command,NULL,NULL,FALSE,EXTENDED_STARTUPINFO_PRESENT,NULL,L"ROOT",&si.StartupInfo,&pi);
 DeleteProcThreadAttributeList(si.lpAttributeList);CloseHandle(parent);
 if(!ok){printf("create_error=%lu\n",GetLastError());return 2;}
 BOOL job=TRUE;BOOL queried=IsProcessInJob(pi.hProcess,NULL,&job);
 printf("{\"game_pid\":%lu,\"parent_pid\":%lu,\"in_job\":%s,\"query_ok\":%s}\n",pi.dwProcessId,parentPid,job?"true":"false",queried?"true":"false");
 CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return queried&&!job?0:1;
}
'''.replace('ROOT',R.parent.as_posix())
p=D/'detached_launcher.cpp';p.write_text(cpp,encoding='utf-8');exe=D/'detached_launcher.exe';vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd=f'"{vc}" >nul && cl /nologo /EHsc /std:c++17 /MT "{p}" /Fe:"{exe}" /Fo:"{D/"detached_launcher.obj"}" user32.lib'
q=subprocess.run('cmd /d /s /c "'+cmd+'"',capture_output=True);assert not q.returncode,q.stdout
p=subprocess.run([str(exe)],capture_output=True);x=dict(command=[str(exe)],stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode,policy='Explorer parent inheritance avoids command Job cleanup; no timeout or kill; no Frida spawn; no debug argument')
(D/'detached_launch.json').write_text(json.dumps(x,indent=2),encoding='utf-8');print(json.dumps(x));sys.exit(p.returncode)
