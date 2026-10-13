import json
import pathlib
import re
import sys

from test_var64_text_refactor import VCVARS, execute


def registration(text, name):
    match = re.search(r"^int " + name + r"\(void\)\s*\{", text, re.M)
    if not match:
        raise ValueError(name)
    end = match.end()
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[match.start():end]


root = pathlib.Path(sys.argv[1]).resolve()
output = pathlib.Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
source = (root / "src/plugin/SDK_RVA/variable64/array64_api.c").read_text(encoding="utf-8")
headers = root / "src/plugin/SDK_RVA"
names = re.search(r"static const char\* g_a64names\[\]=\{[^;]+;", source).group(0)
prefix = f'#include "{(headers / "effect/effect_reg.h").as_posix()}"\n'
prefix += f'#include "{(headers / "trigger/trigger_reg.h").as_posix()}"\n'
prefix += r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char* image;
static int ready, calls, failMask, triggerResult, triggerCalls;
static void* g_a64vt[10][26];
static EffectDef g_a64defs[10];
static TriggerDef g_a64trigger;
static unsigned char* a64_image(void){return image;}
int Effect_RegistryReady(void){return ready;}
int Effect_RegistryRegister(EffectDef* d){
 int i=(int)(d-g_a64defs);++calls;
 if(failMask&(1<<i)){d->state=EFF_STATE_FAILED;return 0;}
 d->state=EFF_STATE_OK;return 1;
}
int Trigger_RegistryRegister(TriggerDef* d){
 if(d!=&g_a64trigger)return -1;++triggerCalls;return triggerResult;
}
void Plugin_Log(const char* fmt,...){(void)fmt;}
static void* __fastcall a64_trigger_factory(void){return NULL;}
static unsigned char __fastcall a64_eval(void* s,void* c){(void)s;(void)c;return 0;}
static void* __fastcall a64_trigger_tip(void* s,void* o,void* c,unsigned char i,int n){(void)s;(void)c;(void)i;(void)n;return o;}
static int __fastcall a64_read(void* s,const TriggerScopeView* v,unsigned int off,long long* o){(void)s;(void)v;(void)off;(void)o;return 0;}
'''
for i in range(10):
    prefix += f"static void* __fastcall a64_factory{i}(void){{return NULL;}}\n"
    prefix += f"static void __fastcall a64_exec{i}(void* s,void* c){{(void)s;(void)c;}}\n"
    prefix += f"static void* __fastcall a64_tip{i}(void* s,void* o,void* c){{(void)s;(void)c;return o;}}\n"
main = r'''
int main(void){
 int cases=0,t,i,k,result,initial,expected,expectedCalls;unsigned char* allocated;
 allocated=(unsigned char*)calloc(1,0x2780000);if(!allocated)return 2;
 image=allocated;ready=0;calls=0;if(Array64_RegisterEffects()!=0||calls)return 3;++cases;
 ready=1;image=NULL;if(Array64_RegisterEffects()!=0||calls)return 4;++cases;image=allocated;
 for(k=0;k<26;++k)*(void**)(image+0x2775698u-8+8*k)=(void*)(size_t)(100+k);
 *(void**)(image+0x277C418u)=(void*)999;
 for(t=0;t<4096;++t){
  initial=(t*37)&1023;failMask=t&1023;expected=expectedCalls=0;calls=0;
  memset(g_a64defs,0,sizeof(g_a64defs));memset(g_a64vt,0,sizeof(g_a64vt));
  for(i=0;i<10;++i){
   if(initial&(1<<i)){g_a64defs[i].state=EFF_STATE_OK;++expected;}
   else{++expectedCalls;if(!(failMask&(1<<i)))++expected;}
  }
  result=Array64_RegisterEffects();if(result!=expected||calls!=expectedCalls)return 5;
  for(i=0;i<10;++i)if(!(initial&(1<<i))){
   EffectDef* d=&g_a64defs[i];
   if(strcmp(d->name,g_a64names[i])||strcmp(d->locKey,"ARRAY64_EFFECT")||!d->factory||!d->exec||!d->tooltip||d->entryParser!=(void*)999)return 6;
   if(g_a64vt[i][0]!=(void*)100||g_a64vt[i][14]!=(void*)d->exec||g_a64vt[i][8]!=(void*)d->tooltip)return 7;
   for(k=1;k<26;++k)if(k!=8&&k!=14&&g_a64vt[i][k]!=(void*)(size_t)(100+k))return 8;
  }
  ++cases;
 }
 for(t=0;t<2;++t){
  memset(&g_a64trigger,0,sizeof(g_a64trigger));triggerCalls=0;triggerResult=t;
  result=Array64_RegisterTriggers();
  if(result!=t||triggerCalls!=1||strcmp(g_a64trigger.name,"check_array64")||strcmp(g_a64trigger.locKey,"PLUGIN_CHECK_ARRAY64"))return 9;
  if(g_a64trigger.parameterTemplate!=TRG_TEMPLATE_VARIABLE||g_a64trigger.factory!=a64_trigger_factory||g_a64trigger.eval!=a64_eval||g_a64trigger.tooltip!=a64_trigger_tip||g_a64trigger.operandReader!=a64_read)return 10;
  ++cases;
 }
 printf("%d/%d Array64 production registration cases; native image and registrar calls mocked; no game calls\n",cases,cases);
 free(allocated);return 0;
}
'''
fixture = prefix + names + "\n" + registration(source, "Array64_RegisterEffects") + "\n" + registration(source, "Array64_RegisterTriggers") + main
(output / "fixture.c").write_text(fixture, encoding="ascii")
command = 'cmd /d /s /c "' + f'"{VCVARS}" >nul && cl /nologo /W3 /TC fixture.c /Fe:fixture.exe' + '"'
process, build = execute(command, output)
result = build
if process.returncode == 0:
    process, result = execute([str(output / "fixture.exe")], output)
(output / "result.json").write_text(json.dumps(dict(build=build, result=result), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
sys.exit(process.returncode)
