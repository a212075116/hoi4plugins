import argparse
import hashlib
import json
import pathlib
import re
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument('source_root', type=pathlib.Path)
parser.add_argument('output', type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
path = root / 'src/plugin/SDK_RVA/effect/effect_reg.c'
text = path.read_text(encoding='utf-8-sig')
start = text.index('void* Effect_BuildTooltip(')
opening = text.index('{', start)
end, depth = opening + 1, 1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
body = text[start:end]
for name, rva, mock in [('GetParamFn', 'GETPARAM', 'GetParam'), ('ParamCtorFn', 'PARAM_CTOR', 'Ctor'),
                        ('ParamDtorFn', 'PARAM_DTOR', 'Dtor'), ('PackKeyFn', 'PACKKEY', 'Pack'),
                        ('FormatFn', 'FORMAT', 'Format'), ('StrAppendFn', 'STR_APPEND', 'Append')]:
    old = f'(({name})(img + RVA_EFF_{rva}))'
    if 'NativeAdapter_RegistryRva(' in body:
        symbols={'GETPARAM':'NS_PARAM_GET','PARAM_CTOR':'NS_PARAM_CTOR','PARAM_DTOR':'NS_PARAM_DTOR','PACKKEY':'NS_TEXT_PACK','FORMAT':'NS_TEXT_FORMAT','STR_APPEND':'NS_TEXT_APPEND'}
        old=f'(({name})(img + NativeAdapter_RegistryRva({symbols[rva]})))'
    assert body.count(old) == 1, old
    body = body.replace(old, mock)
body=re.sub(r'NativeAdapter_RegistryRva\(NS_[A-Z_]+\)','0',body)
fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "@@STRING@@"
#define EFF_PARAMDESC_SIZE 0x68
#define EFF_SSO_MAX 15
#define RVA_EFF_PACKKEY 0
#define RVA_EFF_PARAM_TAG 0
static unsigned char image[16];
static unsigned char* Effect_GetModuleBase(void){return image;}
static int NativeAdapter_RegistryReady(void){return 1;}
static int NativeMemory_IsReadable(const void* p,size_t n){return p!=NULL;(void)n;}
static int g_hasPendingTooltip;
static char g_pendingTooltipText[192];
static const char* g_pendingTooltipLocKey;
static char borrowed[2][512];
static void* owned[2];
static int mode,len,ctors,dtors,appends;
static void Set(void* out,int which){
 NativeString* v=out;char* p;memset(v,0,sizeof(*v));v->size=len;
 if(len<=15){v->cap=15;p=v->u.buf;}
 else{v->cap=len;p=(mode&(1<<which))?(owned[which]=malloc(len+1)):borrowed[which];v->u.ptr=p;}
 memset(p,'x',len);p[len]=0;
}
static void GetParam(void* a,void* v,void* c,int d,int e){*(long long*)v=125000;}
static void Ctor(void* p){++ctors;}
static void Dtor(void* p){++dtors;}
static void Pack(void* p,const char* k,void* d,int n){Set(p,0);}
static void Format(void* p,void* c,void* k){Set(p,1);}
static char outputBuffer[512];
static void Append(void* out,const char* data,size_t n){
 NativeString* v=out;++appends;v->size=n;
 if(n<=15){v->cap=15;memcpy(v->u.buf,data,n);v->u.buf[n]=0;}
 else{v->cap=n;v->u.ptr=outputBuffer;memcpy(outputBuffer,data,n);outputBuffer[n]=0;}
}
@@BODY@@
int main(void){
 int lengths[]={0,1,15,16,32,149,150,191,399,400,511};int i,m,total=0,failed=0,retained=0;
 for(m=0;m<4;++m)for(i=0;i<11;++i){
  NativeString out;unsigned char self[128]={0};int ctx=7,j;
  len=lengths[i];mode=m;ctors=dtors=appends=g_hasPendingTooltip=0;
  owned[0]=owned[1]=NULL;memset(&out,0,sizeof(out));
  if(Effect_BuildTooltip(self,&out,&ctx,"key")!=&out)++failed;
  if(out.size!=(size_t)((len>0&&len<400)?len:0)||ctors!=1||dtors!=1||ctx!=7)++failed;
  if(appends!=(len>0&&len<400)||g_hasPendingTooltip!=(len>0&&len<150))++failed;
  for(j=0;j<2;++j)if(owned[j]){++retained;free(owned[j]);owned[j]=NULL;}
  ++total;
 }
 printf("cases=%d failed=%d modeled_owned_temporaries_retained=%d; mock-owned/borrowed contract only, not game allocator proof\n",total,failed,retained);
 return failed!=0;
}
'''.replace('@@STRING@@', (root / 'src/plugin/SDK_RVA/common/native_string.h').as_posix()).replace('@@BODY@@', body)
(output / 'fixture.c').write_text(fixture, encoding='ascii')
vc = 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
commands = [f'"{vc}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe',
            [str(output / 'fixture.exe')]]
records = []
for command in commands:
    p = subprocess.run(command, cwd=output, capture_output=True, timeout=120, shell=isinstance(command, str))
    records.append(dict(command=command, cwd=str(output), stdout=p.stdout.decode('utf-8', errors='replace'),
                        stderr=p.stderr.decode('utf-8', errors='replace'), exit=p.returncode))
    if p.returncode:
        break
result = dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), commands=records,
              scope='Actual Effect_BuildTooltip body; only RVA callbacks substituted. Owned and borrowed producers modeled. No native producer ownership inference.',
              exit=records[-1]['exit'])
(output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(result['exit'])
