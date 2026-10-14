import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "effect"))
from test_var64_text_refactor import VCVARS, execute

parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
text = (root / "src/plugin/plugin_main.c").read_text(encoding="utf-8")
new = 'RegisterPluginGroups("effects"' in text
if new:
    support = text[text.index("static int RegisterLanguageStep("):text.index("static DWORD WINAPI PluginThread(")]
    begin = text.index('    RegisterPluginGroups("effects"', text.index("static DWORD WINAPI PluginThread("))
else:
    support = ""
    begin = text.index("    {\n        int round;\n        int ok = 0;", text.index("static DWORD WINAPI PluginThread("))
end = text.index("    for (i = 0; i < 300;", begin)
block = text[begin:end]
headers = ""
if new:
    for name in ["plugin_registration.h", "SDK_RVA/effect/effect_camera.h", "SDK_RVA/effect/effect_gamedate.h",
                 "SDK_RVA/variable64/variable64.h", "SDK_RVA/variable64/array64_api.h", "SDK_RVA/trigger/trigger_demo.h"]:
        headers += '#include "' + (root / "src/plugin" / name).as_posix() + '"\n'
fixture = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
HEADERS
static int calls[8],done[8],delay[8],expected[8]={4,5,7,10,1,1,3,1},ticks,readyDelay,hookDelay,syntaxReady,languageReady;
static int checks,failed,duplicates,caseId,failuresLogged;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL case=%d line=%d\n",caseId,__LINE__);}}while(0)
void Plugin_Log(const char* fmt,...){if(strstr(fmt,"incomplete"))++failuresLogged;}
static int Effect_RegistryReady(void){return ticks>=readyDelay;}static int Trigger_RegistryReady(void){return ticks>=readyDelay;}
static void Pause(DWORD n){CHECK(n==10);++ticks;}
#define Sleep Pause
static int reg(int i){++calls[i];if(done[i])++duplicates;if(calls[i]<=delay[i])return expected[i]-1;done[i]=1;return expected[i];}
int EffectCameras_Register(void){return reg(0);}int EffectGameDate_Register(void){return reg(1);}int Var64_RegisterEffects(void){int n=reg(2);syntaxReady=calls[2]>hookDelay;return n;}int Array64_RegisterEffects(void){return reg(3);}int Var64_RegisterLoadGameCommand(void){return reg(4);}
void Var64_InstallLanguageBridge(void){languageReady=reg(5)==1;}int Var64_SyntaxHooksReady(void){return syntaxReady;}int Var64_LanguageBridgeReady(void){return languageReady;}
int TriggerDemo_Register(void){return reg(6);}int Array64_RegisterTriggers(void){return reg(7);}int Effect_RegistryRegisteredCount(void){int n=0;for(int i=0;i<4;++i)n+=done[i]*expected[i];return n;}
SUPPORT
static void Startup(void){BLOCK}
int main(void){for(caseId=0;caseId<521;++caseId){memset(calls,0,sizeof(calls));memset(done,0,sizeof(done));memset(delay,0,sizeof(delay));ticks=duplicates=syntaxReady=languageReady=failuresLogged=0;readyDelay=caseId%7;hookDelay=0;
 if(caseId<512){for(int i=0;i<8;++i)delay[i]=(caseId&(1<<i))?1+(caseId%3):0;hookDelay=(caseId&256)?3:0;}else if(caseId<520)delay[caseId-512]=4000;else hookDelay=4000;
 RESET
 Startup();if(caseId<512){for(int i=0;i<8;++i)CHECK(done[i]);CHECK(syntaxReady&&languageReady);CHECK(ticks<100);}
 else if(caseId<520){CHECK(!done[caseId-512]);for(int i=0;i<8;++i)if(i!=caseId-512)CHECK(done[i]);CHECK(failuresLogged>0);CHECK(ticks>=3000);}
 else{for(int i=0;i<8;++i)CHECK(done[i]);CHECK(!syntaxReady&&failuresLogged>0&&ticks>=3000);}
 for(int i=0;i<8;++i)if(done[i]&&i!=2)CHECK(calls[i]==delay[i]+1);if(done[2]&&caseId!=520)CHECK(calls[2]==(delay[2]>hookDelay?delay[2]:hookDelay)+1);
 }
 printf("bootstrap_cases=521 checks=%d failed=%d;actual startup blocks/poller,controlled registrars,partial/late/permanent/hookreadiness/completedgroup skip\n",checks,failed);return failed?1:0;}
'''
reset = ""
if new:
    reset = "for(int i=0;i<6;++i){g_effectSteps[i].complete=0;g_effectSteps[i].last=0;}for(int i=0;i<2;++i){g_triggerSteps[i].complete=0;g_triggerSteps[i].last=0;}"
fixture = fixture.replace("HEADERS", headers).replace("SUPPORT", support).replace("BLOCK", block).replace("RESET", reset)
(output / "fixture.c").write_text(fixture, encoding="ascii")
p, build = execute('cmd /d /s /c "' + f'"{VCVARS}" >nul && cl /nologo /W3 /TC /MT /O2 fixture.c /Fe:fixture.exe' + '"', output)
if p.returncode:
    result = build
else:
    _, result = execute([str(output / "fixture.exe")], output)
(output / "result.json").write_text(json.dumps(dict(build=build, result=result,
    input_sha256=hashlib.sha256(b"512transient+8permanentgroups+permanenthookreadiness").hexdigest(),
    scope="Actual copied PluginThread registration blocks andnew poller; registrars/readiness/Sleep controlled; not native allocator transfer proof"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
