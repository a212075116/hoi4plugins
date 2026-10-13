import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
VCVARS = pathlib.Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')


def run(command, cwd, timeout=120):
    process = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
    return dict(command=command, cwd=str(cwd), stdout=process.stdout.decode('utf-8', errors='replace'),
                stderr=process.stderr.decode('utf-8', errors='replace'), exit=process.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=pathlib.Path, default=ROOT)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--phase', required=True)
    args = parser.parse_args()
    source, output = args.source_root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    plugin = (source / 'src/plugin/plugin_main.c').read_text(encoding='utf-8')
    start, end = plugin.index('void Plugin_Log('), plugin.index('static void VerifyClassStructure(')
    (output / (args.phase + '_plugin_log.inc')).write_text(plugin[start:end], encoding='utf-8')
    common = source / 'src/plugin/SDK_RVA/common/log.c'
    template = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
static char captured[4096], capturedPath[MAX_PATH], assigned[4096];
static int writes, opens, closes, assigns, useBase = 1;
static DWORD accessFlags, shareFlags;
static HMODULE WINAPI TestModule(LPCSTR name);
static HANDLE WINAPI TestOpen(LPCSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES attr, DWORD disposition, DWORD flags, HANDLE templateFile) {
    (void)attr; (void)disposition; (void)flags; (void)templateFile;
    ++opens; strcpy_s(capturedPath, sizeof(capturedPath), path); accessFlags=access; shareFlags=share; return (HANDLE)(uintptr_t)123;
}
static VOID WINAPI TestTime(LPSYSTEMTIME value) { memset(value,0,sizeof(*value)); value->wHour=1;value->wMinute=2;value->wSecond=3;value->wMilliseconds=4; }
static BOOL WINAPI TestWrite(HANDLE h,LPCVOID data,DWORD n,LPDWORD written,LPOVERLAPPED overlap) {
    (void)h;(void)overlap;++writes;memcpy(captured,data,n);captured[n]=0;*written=n;return TRUE;
}
static BOOL WINAPI TestClose(HANDLE h) {(void)h;++closes;return TRUE;}
#define GetModuleHandleA TestModule
#define CreateFileA TestOpen
#define GetLocalTime TestTime
#define WriteFile TestWrite
#define CloseHandle TestClose
#include "CONSOLE_SOURCE"
#include "CARRIER_HEADER"
COMMON_SOURCE
#include "PLUGIN_LOG"
static void** __fastcall TestAssign(void** destination,const void* data,size_t n) {
    CmdString* s=(CmdString*)destination;++assigns;memcpy(assigned,data,n);assigned[n]=0;s->u.ptr=assigned;s->size=n;s->cap=n;return destination;
}
static HMODULE WINAPI TestModule(LPCSTR name) {(void)name;return useBase?(HMODULE)((uintptr_t)TestAssign-0x129CA0u):NULL;}
static int passed,total;
static void Check(int ok,const char* name) {++total;passed+=!!ok;printf("%s %s\n",ok?"PASS":"FAIL",name);}
int main(void) {
    CmdResult r; char text[2049], dst[64]; CmdString arg; CmdArgs args={&arg,1,1};
    memset(&r,0,sizeof(r));ConsoleCmd_InitResult(&r);Check(!r.ok && !r.message.size && r.message.cap==15,"result-init");
    ConsoleCmd_SetMessage(&r,"123456789012345");Check(r.message.size==15 && r.message.cap==15 && !strcmp(r.message.u.buf,"123456789012345"),"sso-15");
    ConsoleCmd_SetMessage(&r,"1234567890123456");Check(assigns==1 && r.message.size==16 && !strcmp(r.message.u.ptr,"1234567890123456"),"native-assign-16");
    ConsoleCmd_SetMessage(&r,"short");Check(r.message.size==5 && r.message.cap==15 && !strcmp(r.message.u.buf,"short"),"long-to-short-existing-contract");
    memset(&r,0,sizeof(r));r.ok=1;ConsoleCmd_SetMessage(&r,"");Check(!r.message.size && r.message.cap==15 && !r.message.u.buf[0] && r.ok==1,"zero-cap-empty-preserve-ok");
    ConsoleCmd_SetMessage(NULL,"x");ConsoleCmd_SetMessage(&r,NULL);Check(!r.message.size,"null-noop");
    useBase=0;ConsoleCmd_SetMessage(&r,"12345678901234567890");Check(r.message.size==15 && !strcmp(r.message.u.buf,"123456789012345"),"missing-module-fallback");useBase=1;
    ConsoleCmd_WriteString(&arg,"arg");Check(ConsoleCmd_GetArg(&args,0,dst,sizeof(dst)) && !strcmp(dst,"arg"),"short-argument");
    ConsoleCmd_WriteString(&arg,"abcdefghijklmnop");Check(ConsoleCmd_GetArg(&args,0,dst,sizeof(dst)) && !strcmp(dst,"abcdefghijklmnop"),"long-argument");
    Check(!ConsoleCmd_GetArg(&args,1,dst,sizeof(dst)) && !ConsoleCmd_GetArg(&args,-1,dst,sizeof(dst)),"argument-index-bounds");
    ConsoleCmd_DefaultLog("[info] %s %d","fixture",7);Check(!strcmp(captured,"[01:02:03.004] [info] fixture 7\r\n"),"console-log-bytes");
    Check(!strcmp(capturedPath,LOADER_LOG_DIR "/console_cmd.log"),"console-log-path");
    Plugin_Log("[error] %s","fixture");Check(!strcmp(captured,"[01:02:03.004] [error] fixture\r\n"),"plugin-log-bytes");
    Check(!strcmp(capturedPath,LOADER_LOG_DIR "/mod_loader_" CARRIER_LIBRARY ".log"),"plugin-log-path");
    Check(accessFlags==FILE_APPEND_DATA && shareFlags==(FILE_SHARE_READ|FILE_SHARE_WRITE) && opens==writes && closes==writes,"append-share-close-contract");
    memset(text,'x',2047);text[2047]=0;Plugin_Log("%s",text);Check(strlen(captured)==2064 && writes==3,"log-2047-boundary");
    text[2047]='x';text[2048]=0;Plugin_Log("%s",text);ConsoleCmd_DefaultLog("%s",text);Check(writes==3 && opens==3 && closes==3,"log-overflow-drop-no-open");
    printf("%d/%d source behavior checks; native assign and file calls modeled; no game commands executed\n",passed,total);return passed==total?0:1;
}
'''
    cpp = template.replace('CONSOLE_SOURCE', (source/'src/plugin/SDK_RVA/console/console_cmd.c').as_posix())
    cpp = cpp.replace('CARRIER_HEADER', (source/'src/carrier/carrier.h').as_posix())
    cpp = cpp.replace('COMMON_SOURCE', '#include "'+common.as_posix()+'"' if common.exists() else '')
    cpp = cpp.replace('PLUGIN_LOG', (output/(args.phase+'_plugin_log.inc')).as_posix())
    fixture, exe = output/(args.phase+'_source.c'), output/(args.phase+'_source.exe')
    fixture.write_text(cpp, encoding='utf-8')
    cmd = f'"{VCVARS}" >nul && cl /nologo /TC /MT /Gy /I"{source}/src/plugin" /I"{source}/src/carrier" "{fixture}" /Fe:"{exe}" /Fo:"{output}/{args.phase}_source.obj" /link /OPT:REF'
    build = run('cmd /d /s /c "'+cmd+'"', ROOT)
    result = run([str(exe)], ROOT) if not build['exit'] else None
    evidence = dict(source=str(source), phase=args.phase, build=build, result=result,
                    source_hashes={str(source/p):hashlib.sha256((source/p).read_bytes()).hexdigest() for p in ['src/plugin/plugin_main.c','src/plugin/SDK_RVA/console/console_cmd.c']})
    (output/(args.phase+'.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return int(build['exit']!=0 or result is None or result['exit']!=0)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

