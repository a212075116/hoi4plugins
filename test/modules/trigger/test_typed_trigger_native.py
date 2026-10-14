"""Compile actual typed registrar and adapters with controlled native dependencies."""
import ast,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
tree=ast.parse((ROOT/'test/modules/trigger/test_trigger_registry_native.py').read_text())
parts={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and n.targets[0].id in ['prefix','body']}
body=parts['body'].split('int main(void){')[0]
body=body.replace('(void)container;(void)name;(void)out;return 0;','(void)name;if(!container)return 0;*out=*(long long*)container;return 1;')
extra=r'''
static unsigned char* __fastcall valueFactory(void){return calloc(1,304);}
static unsigned char* __fastcall variableFactory(void){return calloc(1,544);}
static unsigned __fastcall scopeMask(void* ctx){return *(unsigned*)ctx;}
static void* __fastcall temporary(void){return NULL;}
static long long* __fastcall param(void* d,long long* out,void* ctx,void* x,unsigned char random){*out=*(long long*)((char*)d+64);return out;}
static void* __fastcall container(void* d,void* c,int* a,int* b,void** e,void** f,void** g,void** h,void** i,void** j){static unsigned char boxes[2][64];void* raw=*(void**)((char*)d+152);int index=strcmp((char*)d+112,"left")==0?0:1;if(!raw)return NULL;memset(boxes[index],0,64);memcpy(boxes[index],raw,8);return boxes[index];}
static long long __fastcall half(void* self,const TriggerScopeView* s){return 50000;}
TRG_VALUE_DEF(val,"native_value","value","VALUE",half)
TRG_VARIABLE_DEF(var,"native_variable","block","BLOCK")
static void descriptor(unsigned char* d,const char* name,long long* slot,long long literal){memset(d,0,208);d[8]=1;if(name){makeString(d+112,name);*(void**)(d+152)=slot;}else d[9]=1;*(long long*)(d+64)=literal;}
int main(void){
 unsigned char ctx[176]={0},v[544]={0};TriggerScopeView view;TriggerDef invalid;long long out=0,a=250000,b=375000;void* instance;
 image=VirtualAlloc(NULL,0x4000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);if(!image)return 2;
 *(void**)(image+RVA_TRIGGER_MAP)=mapObject;*(void**)(mapObject+24)=head;head[25]=1;*(void**)(head+8)=head;
 image[RVA_LEXER_INIT]=image[RVA_LEXER_SYNC]=1;
 thunk(RVA_GAME_ALLOC,alloc);thunk(RVA_GAME_FREE,release);thunk(RVA_ADD_TOKEN,addToken);thunk(RVA_REGISTER_TRIGGER,reg);
 thunk(RVA_VALUE_FACTORY,valueFactory);thunk(RVA_VARIABLE_FACTORY,variableFactory);
 thunk(0x537d90,scopeMask);thunk(0x544c90,param);thunk(0x542500,container);
 thunk(0x54f730,temporary);
 *(void**)(image+RVA_VALUE_VT+4*8)=image+0x13a2690;*(void**)(image+RVA_VALUE_VT+22*8)=image+0x13a2180;
 *(void**)(image+RVA_VALUE_ENTRY_VT+8)=image+RVA_VALUE_FACTORY;
 *(void**)(image+RVA_VARIABLE_VT+4*8)=image+0x54ae70;*(void**)(image+RVA_VARIABLE_VT+22*8)=image+0x3d0bb0;
 *(void**)(image+RVA_VARIABLE_ENTRY_VT+8)=image+RVA_VARIABLE_FACTORY;
 val_fill();var_fill();expect("value_register",Trigger_RegistryRegister(&val_def));expect("block_register",Trigger_RegistryRegister(&var_def));
 expect("value_getter",val_def.vtStorage[24]==val_def.valueGetter);expect("block_parse_preserved",var_def.vtStorage[5]==image+0x54ae70);
 instance=val_factory();expect("value_factory",instance&&*(void**)instance==val_def.vtStorage+1);free(instance);
 instance=var_factory();expect("block_factory",instance&&*(void**)instance==var_def.vtStorage+1);free(instance);
 invalid=var_def;invalid.name="invalid_kind";invalid.state=0;invalid.parameterTemplate=3;expect("invalid_template",!Trigger_RegistryRegister(&invalid));
 invalid=val_def;invalid.name="missing_getter";invalid.state=0;invalid.valueGetter=NULL;expect("missing_getter",!Trigger_RegistryRegister(&invalid));
 expect("null_scope",!Trigger_ScopeView(NULL,&view));*(unsigned*)ctx=2;expect("state_view",Trigger_ScopeView(ctx,&view)&&view.mask==2&&view.nativeContext==ctx);
 descriptor(v+88,"left",&a,999);descriptor(v+296,"right",&b,888);*(int*)(v+504)=468;
 expect("own_left_container",Trigger_ReadRawParameter(v,&view,88,&out)&&out==a);expect("own_right_container",Trigger_ReadRawParameter(v,&view,296,&out)&&out==b);
 expect("block_less",Trigger_EvaluateVariable(v,ctx));expect("block_readonly",a==250000&&b==375000);
 *(int*)(v+504)=14580;expect("block_equal_false",!Trigger_EvaluateVariable(v,ctx));*(int*)(v+504)=14578;expect("block_not_equal",Trigger_EvaluateVariable(v,ctx));
 descriptor(v+296,NULL,NULL,250000);*(int*)(v+504)=14580;expect("literal_fallback",Trigger_EvaluateVariable(v,ctx));
 *(int*)(v+504)=0;expect("invalid_compare",!Trigger_EvaluateVariable(v,ctx));expect("null_instance",!Trigger_EvaluateVariable(NULL,ctx));
 memset(v,0,sizeof(v));descriptor(v+96,NULL,NULL,49999);*(int*)(v+88)=467;expect("scalar_precision",val_eval(v,ctx));
 descriptor(v+96,NULL,NULL,50000);expect("scalar_equal_strict",!val_eval(v,ctx));*(int*)(v+88)=468;expect("scalar_lt_equal_strict",!val_eval(v,ctx));
 *(int*)(v+88)=14580;expect("scalar_invalid_operator",!val_eval(v,ctx));expect("invalid_descriptor_offset",!Trigger_ReadRawParameter(v,&view,97,&out));
 v[104]=0;expect("unset_scalar_parameter",!val_eval(v,ctx));memset(v,0,sizeof(v));*(int*)(v+504)=14581;expect("empty_block",!Trigger_EvaluateVariable(v,ctx));
 {int tokens[]={467,468,14578,14579,14580,14581};long long values[]={(-9223372036854775807LL-1),-1,0,1,9223372036854775807LL};int ok=1;
  for(int i=0;i<5;i++)for(int j=0;j<5;j++)for(int k=0;k<6;k++){long long l=values[i],r=values[j];int want=k==0?l>r:k==1?l<r:k==2?l!=r:k==3?l<=r:k==4?l==r:l>=r;if(Trigger_CompareRaw(l,r,tokens[k])!=want)ok=0;}expect("150_extreme_comparisons",ok);}
 g_scriptFixtureReady=0;expect("binding_scope_gate",!Trigger_ScopeView(ctx,&view));expect("binding_typed_factory_gate",Trigger_NewTypedInstance(&val_def)==NULL);g_scriptFixtureReady=1;
 printf("checks=%d passed=%d failed=%d\n",checks,checks-failures,failures);return failures?1:0;
}
'''
src=(pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c').as_posix()
(out/'fixture.c').write_text(parts['prefix']+'\n#include \"'+(ROOT/'test/lib/native_script_bindings_fixture.h').as_posix()+'\"\n#define RVA_DYNAMIC_COUNT 0x035E1ACCu\n#define RVA_DYNAMIC_TOKENS 0x035E1AC0u\n'+'\n#include "'+src+'"\n'+body+extra,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat';inc=(ROOT/'src/plugin/SDK_RVA/console').as_posix()
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC /I"'+inc+'" fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);r={'command':sys.argv,'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r['stdout']);print('EXIT',p.returncode);raise SystemExit(p.returncode)
