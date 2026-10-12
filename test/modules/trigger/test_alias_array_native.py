import ast,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.stdout.reconfigure(encoding='utf-8',errors='replace')
trg=pathlib.Path(sys.argv[1]).resolve();var=pathlib.Path(sys.argv[2]).resolve();out=pathlib.Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
tree=ast.parse((ROOT/'test/modules/trigger/test_trigger_registry_native.py').read_text());parts={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and n.targets[0].id in ['prefix','body']}
body=parts['body'].split('int main(void){')[0].replace('(void)container;(void)name;(void)out;return 0;','(void)name;if(!container)return 0;*out=*(long long*)container;return 1;')
s=var.read_text(encoding='utf-8-sig')
def fn(n):
 m=re.search(r'(?m)^static[^\n]*\b'+n+r'\(',s);p=m.start();a=s.index('{',p);i=a+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[p:i]+'\n'
prefix='\n#define VAR64_NAME_OFF 200\n#define VAR64_MAIN_NAME_LIMIT 33\n#define VAR64_SUBOBJ_OFF 88\n'
extra=r'''
static unsigned char cont[64],map[64],sentinel[112],node[112],bucket[16];
static void* __fastcall tmp(void){return NULL;}
static void* __fastcall getContainer(void* d,void* c,int* a,int* b,void** e,void** f,void** g,void** h,void** i,void** j){return cont;}
static long long* __fastcall getParam(void* d,long long* out,void* c,void* x,unsigned char random){*out=*(void**)((char*)d+160)?250000:100000;return out;}
int main(void){unsigned char self[544]={0},ctx[176]={0};TriggerScopeView scope={ctx,4};long long value=0;char name[40];
 image=VirtualAlloc(NULL,0x4000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);if(!image)return 2;
 thunk(0x54f730,tmp);thunk(0x542500,getContainer);thunk(0x544c90,getParam);
 *(long long*)cont=1234567890112500LL;self[96]=1;makeString(self+200,"scalar");
 expect("plain_name",Var64_ReadNameOnly(self,name,40));
 expect("plain64",Trigger_ReadRawParameter(self,&scope,88,&value)&&value==1234567890112500LL);
 *(void**)(self+248)=(void*)1;
 expect("index_target_not_scalar",!Var64_ReadNameOnly(self,name,40));
 expect("index_operand_not_scalar",!Var64_ReadOperandNameAt(self,88,name,40));
 expect("index_native_fallback",Trigger_ReadRawParameter(self,&scope,88,&value)&&value==250000);
 *(void**)(self+248)=NULL;makeString(self+200,"num_owned_states");
 *(void**)(cont+48)=map;*(void**)(map+8)=sentinel;*(void**)(map+24)=bucket;*(size_t*)(map+48)=0;
 makeString(node+16,"num_owned_states");*(void**)(node+8)=sentinel;*(void**)bucket=node;*(void**)(bucket+8)=node;
 expect("dynamic_native_priority",Trigger_ReadRawParameter(self,&scope,88,&value)&&value==100000);
 makeString(self+200,"ordinary_name");expect("other_name_still64",Trigger_ReadRawParameter(self,&scope,88,&value)&&value==1234567890112500LL);
 *(void**)(self+232)=(void*)1;expect("compound_target_not_scalar",!Var64_ReadNameOnly(self,name,40));
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failures,failures);return failures?1:0;
}
'''
(out/'fixture.c').write_text(parts['prefix']+'\n#include "'+trg.as_posix()+'"\n'+body+prefix+fn('Var64_ReadNameOnly')+fn('Var64_ReadOperandNameAt')+extra,encoding='ascii')
(out/'trigger_reg.h').write_bytes((ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.h').read_bytes())
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat';inc=(ROOT/'src/plugin/SDK_RVA/console').as_posix()
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC /I"'+inc+'" fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);r={'command':sys.argv,'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode};(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
