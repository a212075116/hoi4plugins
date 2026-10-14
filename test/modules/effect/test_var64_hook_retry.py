import argparse
import hashlib
import json
import pathlib
import re

from test_var64_text_refactor import VCVARS, execute, function

parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
source = root / "src/plugin/SDK_RVA/variable64/variable64.c"
text = source.read_text(encoding="utf-8")
names = ["Add", "Sub", "Mul", "Div", "Clamp", "Clear"]
rvas = "\n".join(line for line in text.splitlines() if re.match(r"#define RVA_VAR_(ADD|SUB|MUL|DIV|CLEAR)_EXEC|#define RVA_VARCLAMP_EXEC", line))
code = function(text, "Var64_InstallArithmeticHooks")
if "int Var64_SyntaxHooksReady(" in text:
    code += function(text.replace("int Var64_SyntaxHooksReady(", "static int Var64_SyntaxHooksReady("), "Var64_SyntaxHooksReady")
fixture = r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef long long (__fastcall *Var64GameSetExecFn)(void*,void*);
static unsigned int failMask,readMask;static int installed[6],calls[6],checks,failed;
static unsigned char* Var64_Image(void){return (unsigned char*)0x10000000;}
RVAS
static unsigned int rvas[6]={RVA_VAR_ADD_EXEC,RVA_VAR_SUB_EXEC,RVA_VAR_MUL_EXEC,RVA_VAR_DIV_EXEC,RVA_VARCLAMP_EXEC,RVA_VAR_CLEAR_EXEC};
static int index(void* p){for(int i=0;i<6;++i)if(p==Var64_Image()+rvas[i])return i;return -1;}
static int ConsoleCmd_IsReadable(const void* p,size_t n){(void)n;int i=index((void*)p);return i>=0&&!(readMask&(1u<<i));}
static long long __fastcall Original(void* a,void* b){(void)a;(void)b;return 123;}
static int g_var64GameSyntaxHookReady=1;static Var64GameSetExecFn g_var64OrigGameSetExec=Original;
void Plugin_Log(const char* fmt,...){(void)fmt;}
static int InlineHook_InstallInto(void* p,void* d,void** out){int i=index(p);(void)d;if(i<0)return 0;++calls[i];if(installed[i]||(failMask&(1u<<i)))return 0;*out=(void*)Original;installed[i]=1;return 1;}
DECLS
CODE
static int ready(void){return READY;}
int main(void){int cases=0;for(unsigned f=0;f<64;++f)for(unsigned r=0;r<64;++r){memset(calls,0,sizeof(calls));memset(installed,0,sizeof(installed));RESET failMask=f;readMask=r;Var64_InstallArithmeticHooks();failMask=readMask=0;Var64_InstallArithmeticHooks();++checks;if(!ready())++failed;for(int i=0;i<6;++i){++checks;if(calls[i]!=(r&(1u<<i)?1:f&(1u<<i)?2:1))++failed;}int before=0;for(int i=0;i<6;++i)before+=calls[i];Var64_InstallArithmeticHooks();int after=0;for(int i=0;i<6;++i)after+=calls[i];++checks;if(before!=after||!ready())++failed;++cases;}printf("hook_retry_cases=%d checks=%d failed=%d;actual arithmetic installer,controlled readability/install ownership,successful originals retained andnot recreated\n",cases,checks,failed);return failed?1:0;}
'''
decls = "".join(f"static Var64GameSetExecFn g_var64Orig{n}Exec;static long long __fastcall Var64_{n}Detour(void* a,void* b){{(void)a;(void)b;return 0;}}\n" for n in names)
reset = "".join(f"g_var64Orig{n}Exec=0;" for n in names)
ready = " && ".join(f"g_var64Orig{n}Exec==(Var64GameSetExecFn)Original" for n in names)
if "int Var64_SyntaxHooksReady(" in text:
    ready = "Var64_SyntaxHooksReady()"
fixture = fixture.replace("RVAS", rvas).replace("DECLS", decls).replace("CODE", code).replace("RESET", reset).replace("READY", ready)
(output / "fixture.c").write_text(fixture, encoding="ascii")
p, build = execute('cmd /d /s /c "' + f'"{VCVARS}" >nul && cl /nologo /W3 /TC /MT /O2 fixture.c /Fe:fixture.exe' + '"', output)
if p.returncode:
    result = build
else:
    _, result = execute([str(output / "fixture.exe")], output)
(output / "result.json").write_text(json.dumps(dict(build=build, result=result,
    input_sha256=hashlib.sha256(b"64installfailure*64unreadable,retry,repeat").hexdigest(),
    scope="Actual six arithmetic hook installer; native dependencies controlled; not MinHook global lifecycle"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
