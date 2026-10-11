import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve()
out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=source.read_text(encoding='utf-8-sig')
start=s.rindex('static int Var64_LangResolveSlotValue(')
end=s.index('static void Var64_LangAppendText(',start)
fn=s[start:end]
prefix=r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define VAR64_NAME_LIMIT 40u
#define VAR64_SSO_LIMIT 15u
#define VAR64_SLOT_SCALE 100000LL
typedef void (__fastcall *Var64CtxResolveFn)(void*,void**,void*);
static int valid=0;
static const char* expectedName;
static int ConsoleCmd_IsReadable(const void* p,size_t n){return p!=NULL;}
static void __fastcall resolve(void* ctx,void** out,void* field){
 unsigned char* f=(unsigned char*)field;
 size_t len=*(unsigned long long*)(f+16),cap=*(unsigned long long*)(f+24);
 const char* str=cap<=15?(char*)f:*(char**)f;
 valid=(len<=cap && len==strlen(expectedName) && memcmp(str,expectedName,len)==0 && str[len]==0);
 *out=valid?(void*)(intptr_t)(150000LL*VAR64_SLOT_SCALE):NULL;
}
'''
suffix=r'''
int main(void){
 const char* names[]={"x_var64f","repro_big_var64f","repro_small_var64f","repro_zero_var64f","abcdefghijklmnopqrstuvwxyz012345_var64f","abcdefghijklmnopqrstuvwxyz0123456_var64f"};
 void* vt[8]={0};void** ctx=vt;int fails=0,i;
 setvbuf(stdout,NULL,_IONBF,0);
 vt[4]=(void*)&resolve;
 for(i=0;i<6;i++){
  long long v=-1;int ok;
  expectedName=names[i];valid=0;
  ok=Var64_LangResolveSlotValue(&ctx,names[i],&v);
  printf("name=%s len=%zu layout_valid=%d value=%lld expected=150000 return=%d\n",names[i],strlen(names[i]),valid,v,ok);
  if(!valid || v!=150000 || !ok)fails++;
 }
 printf("checks=6 passed=%d failed=%d\n",6-fails,fails);
 return fails?1:0;
}
'''
(out/'fixture.c').write_text(prefix+fn+suffix,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
r=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
print('BUILD_EXIT',r.returncode)
if r.returncode:
 print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(r.returncode)
r=subprocess.run([str(out/'fixture.exe')],capture_output=True)
sys.stdout.write(r.stdout.decode('ascii'));sys.stderr.write(r.stderr.decode('ascii'))
raise SystemExit(r.returncode)
