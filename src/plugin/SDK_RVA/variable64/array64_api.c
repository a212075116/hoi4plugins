#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "array64_api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "console_cmd.h"
#include "effect_reg.h"
#include "trigger_reg.h"
#include "file_redirect.h"
#include "array64_shape_journal.c"

extern void Plugin_Log(const char* fmt,...);
typedef void* (__fastcall *A64Lookup)(void*,void*,long long);
typedef void (__fastcall *A64Erase)(void*,void*);
typedef void* (__fastcall *A64Resolve)(void*,void*,int*,int*,void**,void**,void**,void**,void**,void**);
typedef void* (__fastcall *A64Factory)(void);
typedef void* (__fastcall *A64Append)(void*,const char*,size_t);
typedef LONG (WINAPI *A64Random)(void*,unsigned char*,ULONG,ULONG);
static unsigned char* a64_image(void){return (unsigned char*)GetModuleHandleA(NULL);}

int na_read_memory(const void* source,void* output,NaSize bytes)
{
    if(bytes>4096||!ConsoleCmd_IsReadable(source,(size_t)bytes))return 0;
    __try{memcpy(output,source,(size_t)bytes);return 1;}__except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
int as_native_put(void* c,const char* key,long long raw)
{
    struct {const char* data;unsigned long long length;} view;long long* p;unsigned char* image=a64_image();
    if(!image||!c||!key||!ConsoleCmd_IsReadable(c,56))return 0;view.data=key;view.length=strlen(key);
    __try{p=((A64Lookup)(image+0xBC5C10u))(c,&view,0);if(!ConsoleCmd_IsReadable(p,8))return 0;*p=raw;return 1;}
    __except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
int as_native_erase(void* c,const char* key)
{
    struct {const char* data;unsigned long long length;} view;long long raw;unsigned char* image=a64_image();
    if(!image||na_lookup(c,key,&raw)!=1)return 0;view.data=key;view.length=strlen(key);
    __try{((A64Erase)(image+0xBC8FC0u))(c,&view);return na_lookup(c,key,&raw)==0;}
    __except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
int tx_write_existing(void* c,const char* key,long long raw){long long prior;return na_lookup(c,key,&prior)==1&&as_native_put(c,key,raw);}

static int a64_random(unsigned int* words,int count)
{
    static HMODULE module;static A64Random random;
    if(!module)module=LoadLibraryA("bcrypt.dll");if(!module)return 0;
    if(!random)random=(A64Random)GetProcAddress(module,"BCryptGenRandom");
    if(!random||random(NULL,(unsigned char*)words,(ULONG)(count*4),2)!=0)return 0;
    for(int i=0;i<count;++i){words[i]&=2147483647u;if(!words[i])words[i]=1;}return 1;
}

static int a64_identity(void* c,int create,char scope[40],unsigned long long* lineage)
{
    unsigned int words[4];long long raw;int found=0;char key[32];
    for(int i=0;i<4;++i){sprintf_s(key,sizeof(key),"__v64sys_id%d",i);int status=na_lookup(c,key,&raw);
        if(status<0)return 0;if(status){if(raw<100000||raw%100000||raw/100000>2147483647LL)return 0;words[i]=(unsigned int)(raw/100000);++found;}}
    if(found!=4){
        if(found||!create||!a64_random(words,4))return 0;
        for(int i=0;i<4;++i){sprintf_s(key,sizeof(key),"__v64sys_id%d",i);if(!as_native_put(c,key,words[i]*100000LL))return 0;}
    }
    sprintf_s(scope,40,"scope:%08X%08X%08X%08X",words[0],words[1],words[2],words[3]);
    *lineage=((unsigned long long)words[0]<<32)|words[1];return 1;
}

static int a64_target(void* self,void* ctx,unsigned int offset,void** container,char name[21],int* index,int* indexed,int* count_index)
{
    unsigned char* d=(unsigned char*)self+offset;unsigned char* text;unsigned long long len,cap;int a=0,b=0;void* extra[6]={0};
    TriggerScopeView view;long long raw;char roots[6][40];void* selector;
    if(!self||!ctx||!ConsoleCmd_IsReadable(d,208)||!d[8]||d[9]||d[10]||d[11]||d[14]||
        *(void**)(d+144)||*(void**)(d+168))return 0;
    len=*(unsigned long long*)(d+128);cap=*(unsigned long long*)(d+136);text=cap<=15?d+112:*(unsigned char**)(d+112);
    if(!len||len>20||len>cap||!ConsoleCmd_IsReadable(text,(size_t)len+1)||text[len]||memchr(text,0,(size_t)len))return 0;
    memcpy(name,text,(size_t)len);name[len]=0;if(!ag_name(name,roots))return 0;
    *container=((A64Resolve)(a64_image()+0x542500u))(d,ctx,&a,&b,&extra[0],&extra[1],&extra[2],&extra[3],&extra[4],&extra[5]);
    if(!*container||!ConsoleCmd_IsReadable(*container,56))return 0;
    selector=*(void**)(d+160);*indexed=selector!=NULL;*index=0;*count_index=0;
    if(selector){
        if(!ConsoleCmd_IsReadable(selector,208))return 0;
        if(*((unsigned char*)selector+152)){*count_index=1;*index=-1;return 1;}
        if(!Trigger_ScopeView(ctx,&view))return 0;
        typedef long long* (__fastcall *ParamFn)(void*,long long*,void*,void*,unsigned char);
        if(*((unsigned char*)selector+11))return 0;
        ((ParamFn)(a64_image()+0x544C90u))(selector,&raw,ctx,NULL,0);
        if(raw<0||raw%100000||raw/100000>4096)return 0;*index=(int)(raw/100000);
    }
    return 1;
}

static int a64_read(void* self,const TriggerScopeView* view,unsigned int offset,long long* out)
{
    void* c;char name[21];int index,indexed,count_index,n,g,status;
    if(offset!=88)return Trigger_ReadRawParameter(self,view,offset,out);
    if(!view||!a64_target(self,view->nativeContext,88,&c,name,&index,&indexed,&count_index)||!indexed)return 0;
    status=Array64Group_Read(c,name,index,-1,out,&n,&g);
    if(count_index&&status==2){*out=n*100000LL;return 1;}return status==1;
}

static int a64_path(const char* scope,const char* name,char path[MAX_PATH])
{
    char folder[MAX_PATH];const char* root=FileRedirect_GameRoot();if(!root||strlen(root)>150)return 0;
    sprintf_s(folder,sizeof(folder),"%s/reports/array64_journal",root);
    if(!CreateDirectoryA(folder,NULL)&&GetLastError()!=ERROR_ALREADY_EXISTS)return 0;
    sprintf_s(folder,sizeof(folder),"%s/reports/array64_journal/%s",root,scope+6);
    if(!CreateDirectoryA(folder,NULL)&&GetLastError()!=ERROR_ALREADY_EXISTS)return 0;
    return sprintf_s(path,MAX_PATH,"%s/%s.a64j",folder,name)>0;
}

static int a64_load(const char* path,unsigned char* bytes,unsigned int* size)
{
    HANDLE file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);DWORD n,read;
    if(file==INVALID_HANDLE_VALUE)return 0;n=GetFileSize(file,NULL);
    if(n<130||n>100000){CloseHandle(file);return 0;}
    int ok=ReadFile(file,bytes,n,&read,NULL)&&read==n;CloseHandle(file);if(ok)*size=n;return ok;
}

static int a64_store(const char* path,const unsigned char* bytes,unsigned int size,unsigned int nonce)
{
    char temp[MAX_PATH];DWORD wrote;unsigned char* check=(unsigned char*)malloc(100000);unsigned int n;int ok;
    if(!check)return 0;sprintf_s(temp,sizeof(temp),"%s.%lu.%u.tmp",path,(unsigned long)GetCurrentProcessId(),nonce);
    HANDLE f=CreateFileA(temp,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f==INVALID_HANDLE_VALUE){free(check);return 0;}
    ok=WriteFile(f,bytes,size,&wrote,NULL)&&wrote==size&&FlushFileBuffers(f);CloseHandle(f);
    if(ok)ok=MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
    if(ok)ok=a64_load(path,check,&n)&&n==size&&memcmp(check,bytes,size)==0;
    if(!ok)DeleteFileA(temp);free(check);return ok;
}

static void a64_status(void* c,const char* operation,const char* name,int code)
{
    if(c)as_native_put(c,"__v64sys_status",code*100000LL);
    Plugin_Log("[array64] %s name=%s status=%d",operation,name?name:"?",code);
}

static void a64_execute(void* self,void* ctx,int operation,int native_mode)
{
    void* c=NULL;char name[21]="?",scope[40],path[MAX_PATH],shown[48];int index,indexed,count_index,n,g,status=-901,size=0;
    unsigned long long lineage;long long rhs=0,value=0;unsigned int stamps[8],nonce[4],bytes=0;TriggerScopeView view;
    unsigned char* record=NULL;Array64Journal* journal=NULL;Array64ShapeWork* work=NULL;const char* opname;
    static const char* labels[]={"create","append","insert","erase","clear","resize","set","recover","log"};
    opname=labels[operation];
    if(!a64_target(self,ctx,88,&c,name,&index,&indexed,&count_index)||count_index)goto done;
    if(operation!=8&&((operation==2||operation==3||operation==6)!=indexed))goto done;
    if(operation==8){
        if(Array64Group_Read(c,name,indexed?index:-1,-1,&value,&n,&g)==(indexed?1:2)){
            Trigger_FormatRaw(indexed?value:n*100000LL,shown,sizeof(shown));Plugin_Log("[array64-value] %s^%d=%s gen=%d",name,indexed?index:-1,shown,g);status=0;
        }else status=-904;goto done;
    }
    if(operation!=7&&(!Trigger_ScopeView(ctx,&view)||!Trigger_ReadRawParameter(self,&view,296,&rhs)))goto done;
    if(operation==0||operation==5){if(rhs<0||rhs%100000||rhs/100000>4096)goto done;size=(int)(rhs/100000);rhs=0;}
    if(operation==0){char roots[6][40];int owned;if(!ag_name(name,roots)||!ag_inventory(c,roots,&owned)||owned||!as_owner_absent(c,name)||!aj_absent(c,name)){status=-2;goto done;}}
    if(!a64_identity(c,operation==0,scope,&lineage)){status=-902;goto done;}
    if(!a64_path(scope,name,path)){status=-903;goto done;}
    record=(unsigned char*)malloc(100000);journal=(Array64Journal*)malloc(sizeof(*journal));work=(Array64ShapeWork*)malloc(sizeof(*work));
    if(!record||!journal||!work){status=-903;goto done;}
    if(operation==7){
        if(!a64_load(path,record,&bytes)){status=-903;goto done;}
        int result=Array64_JournalRecover(c,name,scope,lineage,record,bytes,journal,0);
        if(result==1)status=0;else{
            int finalized=Array64_JournalFinish(c,name,scope,lineage,record,bytes,journal,1);
            if(finalized<0)finalized=Array64_JournalFinish(c,name,scope,lineage,record,bytes,journal,2);
            status=finalized>0?0:result;
        }goto done;
    }
    if(operation==0){g=0;if(!a64_random(stamps,8)){status=-903;goto done;}}
    else if(Array64Group_Read(c,name,-1,-1,&value,&n,&g)!=2){status=-904;goto done;}
    if(!a64_random(nonce,4)){status=-903;goto done;}
    status=Array64_JournalPrepare(c,name,scope,lineage,operation,index,g,rhs,native_mode?0:1,size,operation==0?stamps:NULL,nonce,record,100000,&bytes,journal);
    if(status!=1)goto done;
    if(!a64_store(path,record,bytes,nonce[0])){status=-903;goto done;}
    status=Array64_JournalBegin(c,name,scope,lineage,record,bytes,journal);if(status!=1)goto done;
    status=Array64_JournalApply(c,name,scope,lineage,record,bytes,journal,work,0,0);
    if(status==1)status=0;
done:
    a64_status(c,opname,name,status);free(record);free(journal);free(work);
}

static void* g_a64vt[10][26];
static EffectDef g_a64defs[10];
static const char* g_a64names[]={"create_array64","append_array64","insert_array64","erase_array64","clear_array64","resize_array64","set_array_element64","set_array_element_native","recover_array64","log_array64"};
static void* a64_factory(int i){void* instance=((A64Factory)(a64_image()+0x341F60u))();if(instance)*(void**)instance=g_a64vt[i]+1;return instance;}
static void* a64_tip(void* self,void* out,void* ctx,int i)
{
    char text[256],name[21]="?",value[48]="runtime";unsigned char* d=(unsigned char*)self+88;unsigned char* p=(unsigned char*)self+296;
    (void)ctx;
    if(ConsoleCmd_IsReadable(d,208)){unsigned long long n=*(unsigned long long*)(d+128),cap=*(unsigned long long*)(d+136);const char* s=cap<=15?(char*)d+112:*(const char**)(d+112);
        if(n>0&&n<=20&&ConsoleCmd_IsReadable(s,(size_t)n)){memcpy(name,s,(size_t)n);name[n]=0;}}
    if(ConsoleCmd_IsReadable(p,208)&&p[9])Trigger_FormatRaw(*(long long*)(p+64),value,sizeof(value));
    sprintf_s(text,sizeof(text),"Array64 %s: %s; value=%s (journaled)\n",g_a64names[i],name,value);
    if(out){memset(out,0,32);*(unsigned long long*)((unsigned char*)out+24)=15;((A64Append)(a64_image()+0x129C10u))(out,text,strlen(text));}return out;
}
#define A64_EFFECT(N, OP, MODE) \
    static void* __fastcall a64_factory##N(void){return a64_factory(N);} \
    static void __fastcall a64_exec##N(void* s,void* c){a64_execute(s,c,OP,MODE);} \
    static void* __fastcall a64_tip##N(void* s,void* o,void* c){return a64_tip(s,o,c,N);}
A64_EFFECT(0,0,0) A64_EFFECT(1,1,0) A64_EFFECT(2,2,0) A64_EFFECT(3,3,0) A64_EFFECT(4,4,0)
A64_EFFECT(5,5,0) A64_EFFECT(6,6,0) A64_EFFECT(7,6,1) A64_EFFECT(8,7,0) A64_EFFECT(9,8,0)

int Array64_RegisterEffects(void)
{
    void* (__fastcall *factories[])(void)={a64_factory0,a64_factory1,a64_factory2,a64_factory3,a64_factory4,a64_factory5,a64_factory6,a64_factory7,a64_factory8,a64_factory9};
    EffectExecFn executes[]={a64_exec0,a64_exec1,a64_exec2,a64_exec3,a64_exec4,a64_exec5,a64_exec6,a64_exec7,a64_exec8,a64_exec9};
    void* (*tips[])(void*,void*,void*)={a64_tip0,a64_tip1,a64_tip2,a64_tip3,a64_tip4,a64_tip5,a64_tip6,a64_tip7,a64_tip8,a64_tip9};
    int count=0;unsigned char* image=a64_image();if(!image||!Effect_RegistryReady())return 0;
    for(int i=0;i<10;++i){
        EffectDef* def=&g_a64defs[i];if(def->state==EFF_STATE_OK){++count;continue;}
        g_a64vt[i][0]=*(void**)(image+0x2775698u-8);
        for(int k=0;k<25;++k)g_a64vt[i][k+1]=*(void**)(image+0x2775698u+8*k);
        g_a64vt[i][14]=(void*)executes[i];g_a64vt[i][8]=(void*)tips[i];
        def->name=g_a64names[i];def->desc="Journaled explicit Array64 operation, native var/value syntax.";def->locKey="ARRAY64_EFFECT";
        def->exec=executes[i];def->factory=factories[i];def->tooltip=tips[i];def->entryParser=*(void**)(image+0x277C418u);
        if(Effect_RegistryRegister(def))++count;
    }
    Plugin_Log("[array64] effects=%d/10",count);return count;
}

static TriggerDef g_a64trigger;
static void* __fastcall a64_trigger_factory(void){return Trigger_NewTypedInstance(&g_a64trigger);}
static unsigned char __fastcall a64_eval(void* self,void* ctx)
{
    TriggerScopeView view;long long left,right;if(!Trigger_ScopeView(ctx,&view)||!a64_read(self,&view,88,&left)||!a64_read(self,&view,296,&right))return 0;
    return (unsigned char)Trigger_CompareRaw(left,right,*(int*)((unsigned char*)self+504));
}
static void* __fastcall a64_trigger_tip(void* s,void* out,void* ctx,unsigned char inv,int indent){return Trigger_TypedTooltip(&g_a64trigger,s,out,ctx,inv,indent);}
int Array64_RegisterTriggers(void)
{
    g_a64trigger.name="check_array64";g_a64trigger.desc="Explicit persistent Array64 element/count comparison.";g_a64trigger.locKey="PLUGIN_CHECK_ARRAY64";
    g_a64trigger.parameterTemplate=TRG_TEMPLATE_VARIABLE;g_a64trigger.factory=a64_trigger_factory;g_a64trigger.eval=a64_eval;
    g_a64trigger.tooltip=a64_trigger_tip;g_a64trigger.operandReader=a64_read;
    int ok=Trigger_RegistryRegister(&g_a64trigger);Plugin_Log("[array64] trigger=%d/1",ok);return ok;
}
