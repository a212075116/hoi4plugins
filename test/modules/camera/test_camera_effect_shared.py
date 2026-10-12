import pathlib,hashlib,json,subprocess,sys,re
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True);s=source.read_text(encoding='utf-8-sig')
def function(name):
    m=re.search(r'static [^;{}\n]+\b'+name+r'\(',s)
    if not m:return ''
    a=s.index('{',m.start());b=a+1;depth=1
    while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[m.start():b]+'\n'
parts=''.join(function(n) for n in ['CameraEffect_ReadCurrentHeight','CameraEffect_WriteHeight','ExecSetCamHeight','ExecAddCamHeight','ExecSetLowerLimit','ExecSetUpperLimit'])
prefix=r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#define OFF_CAM_HEIGHT 0x69C
#define OFF_CAM_MINH 0x6D0
#define OFF_CAM_MAXH 0x6D4
#define RVA_CAM_SETH 0
typedef void (__fastcall *CamSetHeightFn)(void*,float);
static unsigned char camera[2048];static int missing,unreadable,fail,shared,legacy,lower,upper,g_cameraEffectExecCount,async_mode;static float parameter,last;
static void legacySpy(void* c,float h){++legacy;*(float*)((unsigned char*)c+OFF_CAM_HEIGHT)=h;}
static HMODULE FakeModule(void* unused){(void)unused;return (HMODULE)legacySpy;}
#define GetModuleHandleA FakeModule
static void Plugin_Log(const char* fmt,...){(void)fmt;}
static void Effect_FlushPendingTooltip(void){}
static void* Camera_GetObject(void){return missing?NULL:camera;}
static float Effect_ParamFloat(void* self,void* scope){(void)self;(void)scope;return parameter;}
static int Camera_SetHeight(void* c,float h){++shared;last=h;if(fail)return 0;*(float*)((unsigned char*)c+OFF_CAM_HEIGHT)=h;return 1;}
static int Camera_GetLimits(void* c,int* lo,int* hi){if(unreadable)return 0;*lo=*(int*)((unsigned char*)c+OFF_CAM_MINH);*hi=*(int*)((unsigned char*)c+OFF_CAM_MAXH);return 1;}
static int Camera_TrueLower(void){return 35;}static int Camera_TrueUpper(void* c){(void)c;return 3000;}
static int Camera_SetLowerLimitSmooth(void* c,int n){++lower;last=(float)n;if(!async_mode)*(int*)((unsigned char*)c+OFF_CAM_MINH)=n;return 1;}
static int Camera_SetUpperLimitSmooth(void* c,int n){++upper;last=(float)n;if(!async_mode)*(int*)((unsigned char*)c+OFF_CAM_MAXH)=n;return 1;}
static void Effect_SetParamFixed(void* self,double n){(void)self;parameter=(float)n;}
'''
main=r'''
static int checks,failed;
static void check(const char* name,int ok){++checks;if(!ok){++failed;printf("FAIL %s\n",name);}}
static void reset(void){memset(camera,0xA5,sizeof(camera));*(float*)(camera+OFF_CAM_HEIGHT)=500;*(int*)(camera+OFF_CAM_MINH)=35;*(int*)(camera+OFF_CAM_MAXH)=3000;missing=unreadable=fail=shared=legacy=lower=upper=async_mode=0;last=0;}
int main(void){
 reset();parameter=950.25f;ExecSetCamHeight(NULL,NULL);check("set_shared",shared==1&&legacy==0&&last==950.25f);check("set_value",*(float*)(camera+OFF_CAM_HEIGHT)==950.25f);check("set_guards",camera[0]==0xA5&&camera[0x698]==0xA5);
 reset();parameter=-50.5f;ExecAddCamHeight(NULL,NULL);check("add_shared",shared==1&&legacy==0&&last==449.5f);check("add_value",*(float*)(camera+OFF_CAM_HEIGHT)==449.5f);
 reset();parameter=0;ExecAddCamHeight(NULL,NULL);check("zero_shared",shared==1&&legacy==0&&last==500);
 reset();missing=1;parameter=99;ExecSetCamHeight(NULL,NULL);ExecAddCamHeight(NULL,NULL);check("no_camera_no_write",shared==0&&legacy==0&&*(float*)(camera+OFF_CAM_HEIGHT)==500);
 reset();fail=1;parameter=900;ExecSetCamHeight(NULL,NULL);check("shared_failure_no_legacy",shared==1&&legacy==0&&*(float*)(camera+OFF_CAM_HEIGHT)==500);
 reset();parameter=-100;ExecSetLowerLimit(NULL,NULL);check("lower_clamp_shared",lower==1&&last==35);reset();parameter=9999;ExecSetUpperLimit(NULL,NULL);check("upper_clamp_shared",upper==1&&last==3000);
 reset();unreadable=1;parameter=100;ExecSetLowerLimit(NULL,NULL);ExecSetUpperLimit(NULL,NULL);check("bad_limits_no_write",lower==0&&upper==0);
 reset();async_mode=1;parameter=100;ExecSetLowerLimit(NULL,NULL);check("lower_preserves_requested_parameter",parameter==100);
 reset();async_mode=1;parameter=2500;ExecSetUpperLimit(NULL,NULL);check("upper_preserves_requested_parameter",parameter==2500);
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+parts+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);r={'command':sys.argv,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'controlled_camera_adapter_not_game':True};(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
