"""Compile actual Effect declarations, batch registrar and scalar registration glue."""
import argparse
import hashlib
import json
import random
from pathlib import Path

from test_var64_text_refactor import VCVARS, execute


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();source=args.source.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    text=source.read_text(encoding='utf-8-sig')
    definitions=text[text.index('EFF_DEF(gamesetvar64,'):text.index('static void Var64_InstallArithmeticHooks(')]
    register=text[text.index('int Var64_RegisterEffects('):]
    registry=(source.parent.parent/'effect/effect_reg.c').read_text(encoding='utf-8-sig')
    registry=registry[registry.index('int Effect_RegistryRegisterAll('):registry.index('int Effect_RegistryRegisteredCount(')]
    header=source.parent.parent/'effect/effect_reg.h'
    fixture=r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "EFFECT_HEADER"
typedef void* (__fastcall *Var64FactoryFn)(void);
static int ready,image,afterStates,batchIndex,hookOrder;
static void* gameEntry=(void*)(uintptr_t)48879;
#define RVA_VARSET_ENTRYVT 0x277C418u
static unsigned char* Var64_Image(void){return image?(unsigned char*)((uintptr_t)&gameEntry-RVA_VARSET_ENTRYVT):NULL;}
static void Plugin_Log(const char* format,...){(void)format;}
static void __fastcall ExecVar64GameSyntax(void* self,void* scope){(void)self;(void)scope;}
void* Effect_NewInstance(void* vt){(void)vt;return (void*)3328;}
void* Effect_BuildTooltip(void* a,void* b,void* c,const char* d){(void)a;(void)b;(void)c;(void)d;return NULL;}
static unsigned int __fastcall Scope(void* self){(void)self;return 42;}
static void* __fastcall Var64_SetVariable64Factory(void){return (void*)1;}
static void* __fastcall Var64_AddToVariable64Factory(void){return (void*)2;}
static void* __fastcall Var64_LogVariable64Factory(void){return (void*)3;}
static void* __fastcall Var64_ModuloVariable64Factory(void){return (void*)4;}
static void* __fastcall Var64_RoundVariable64Factory(void){return (void*)5;}
static void* __fastcall Var64_ClampVariable64Factory(void){return (void*)6;}
static void* __fastcall Var64_ClampHighVariable64Factory(void){return (void*)7;}
int Effect_RegistryReady(void){return ready;}
int Effect_RegistryRegister(EffectDef* def){int divisor=1,i;for(i=0;i<batchIndex;++i)divisor*=3;if((uintptr_t)def->factory()!=(uintptr_t)(batchIndex+1))exit(3);def->state=(afterStates/divisor)%3;def->tokenId=900+batchIndex;++batchIndex;return def->state==EFF_STATE_OK;}
REGISTRY
static void Var64_InstallGameSyntaxHook(void){hookOrder=hookOrder*10+1;}
static void Var64_InstallArithmeticHooks(void){hookOrder=hookOrder*10+2;}
DEFINITIONS
REGISTER
static unsigned long long textHash(const char* text,unsigned long long hash){while(*text){hash^=(unsigned char)*text++;hash*=1099511628211ULL;}return (hash^10)*1099511628211ULL;}
int main(void){int beforeStates;EffectDef* definitions[]={&gamesetvar64_def,&gameaddvar64_def,&gamelogvar64_def,&gamemodvar64_def,&gamerndvar64_def,&gameclpvar64_def,&gameclhvar64_def};
 while(scanf_s("%d %d %d %d",&ready,&image,&beforeStates,&afterStates)==4){int i,divisor=1,result,successful=0;unsigned long long metadata=14695981039346656037ULL;
  for(i=0;i<7;++i){memset(definitions[i],0,sizeof(*definitions[i]));definitions[i]->state=(beforeStates/divisor)%3;definitions[i]->tokenId=800+i;definitions[i]->supportedScopes=Scope;definitions[i]->entryVt[0]=(void*)(uintptr_t)(28672+i);definitions[i]->entryVt[1]=(void*)(uintptr_t)(24576+i);divisor*=3;}
  batchIndex=hookOrder=0;result=Var64_RegisterEffects();printf("%d %d %d",result,batchIndex,hookOrder);
  for(i=0;i<7;++i){EffectDef* d=definitions[i];uintptr_t factory=(uintptr_t)d->factory();if(factory!=(uintptr_t)(i+1)||d->supportedScopes!=Scope||d->exec!=ExecVar64GameSyntax||!d->tooltip)return 4;
   if(ready&&d->state==EFF_STATE_OK)++successful;metadata=textHash(d->name,metadata);metadata=textHash(d->desc,metadata);metadata=textHash(d->locKey,metadata);
   printf(" %llu,%d,%d,%llu,%llu",(unsigned long long)factory,d->state,d->tokenId,(unsigned long long)(uintptr_t)d->entryVt[0],(unsigned long long)(uintptr_t)d->entryVt[1]);
  }
  if(result!=successful||hookOrder!=12)return 5;printf(" %llu\n",metadata);
 }
 return 0;
}
'''.replace('EFFECT_HEADER',header.as_posix()).replace('REGISTRY',registry).replace('DEFINITIONS',definitions).replace('REGISTER',register)
    fixture=fixture.replace('#include <stdio.h>','#include <stdio.h>\n#include <stdlib.h>\n#include "'+(source.parent/"variable64.h").as_posix()+'"')
    (output/'fixture.c').write_text(fixture,encoding='ascii')
    command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    cases=[(ready,image,before,after) for ready in [0,1] for image in [0,1] for before in [0,1093,2186] for after in range(2187)]
    randomizer=random.Random(20261017);cases.extend((randomizer.randrange(2),randomizer.randrange(2),randomizer.randrange(2187),randomizer.randrange(2187)) for _ in range(1024))
    inputs=''.join('%d %d %d %d\n'%case for case in cases).encode();(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs);(output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr)
    assert process.returncode==0 and len(process.stdout.splitlines())==len(cases)
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=len(cases),input_sha256=hashlib.sha256(inputs).hexdigest(),seed=20261017,build=build,result=result,
                scope='Actual EFF_DEF declarations, synchronous registry batch and RegisterEffects; ready/state/entryVT/hooks/factories modeled; no game or native object allocation')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    raise SystemExit(main())
