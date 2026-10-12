import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
base=(pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else root/'src/plugin/SDK_RVA/variable64/native_array_readonly.c').read_text(encoding='utf-8')
group=(pathlib.Path(sys.argv[3]) if len(sys.argv)>3 else root/'src/plugin/SDK_RVA/variable64/array64_group_readonly.c').read_text(encoding='utf-8').replace('#include "native_array_readonly.c"',base)
prefix=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
static unsigned char header[48],nodes[32768*48];static char strings[20000][64];static int used,fault;
int na_read_memory(const void* p,void* out,unsigned long long n){uintptr_t a=(uintptr_t)p,h=(uintptr_t)header,b=(uintptr_t)nodes,s=(uintptr_t)strings;
 if(fault||!p||n>4096)return 0;
 if((a>=h&&a-h<=sizeof(header)&&n<=sizeof(header)-(a-h))||(a>=b&&a-b<=sizeof(nodes)&&n<=sizeof(nodes)-(a-b))||(a>=s&&a-s<=sizeof(strings)&&n<=sizeof(strings)-(a-s))){memcpy(out,p,(size_t)n);return 1;}return 0;}
'''
main=r'''
static unsigned hash(const char* s){unsigned h=2166136261u;while(*s)h=(h^(unsigned char)*s++)*16777619u;return h;}
static void reset(unsigned mask){memset(header,0,sizeof(header));memset(nodes,0,sizeof(nodes));*(void**)(header+24)=nodes;*(unsigned*)(header+36)=mask;header[40]=32;used=0;fault=0;}
static const char* nameat(unsigned char* p){return *(uint64_t*)(p+32)<=15?(const char*)p+8:*(const char**)(p+8);}
static void put(const char* n,long long raw){unsigned h=hash(n),mask=*(unsigned*)(header+36);unsigned char entry[48]={0},tmp[48],*p=nodes+(h&mask)*48,*q=p;
 while(q[4]){if(!strcmp(nameat(q),n)){*(long long*)(q+40)=raw;return;}q+=48;}
 *(unsigned*)entry=h;entry[4]=1;*(uint64_t*)(entry+24)=strlen(n);*(uint64_t*)(entry+32)=strlen(n)<=15?15:63;
 if(strlen(n)<=15)memcpy(entry+8,n,strlen(n));else{strcpy_s(strings[used],64,n);*(void**)(entry+8)=strings[used++];}
 *(long long*)(entry+40)=raw;while(p[4]){if(p[4]<entry[4]){memcpy(tmp,p,48);memcpy(p,entry,48);memcpy(entry,tmp,48);}p+=48;entry[4]++;}memcpy(p,entry,48);}
static void keyput(const char* name,const char* suffix,long long raw){char key[64];sprintf_s(key,64,"__v64a_%s_%s",name,suffix);put(key,raw);}
static void element(const char* name,int index,long long raw,int wide){char key[64];uint64_t bits=(uint64_t)raw;long long lo=(long long)(bits&0xffffffffu),hi=(long long)(bits>>32);
 if(lo>=2147483648LL)lo-=4294967296LL;if(hi>=2147483648LL)hi-=4294967296LL;
 sprintf_s(key,64,"lo^%d",index);keyput(name,key,wide?(lo==-2147483648LL?0:lo*100000):raw);sprintf_s(key,64,"hi^%d",index);keyput(name,key,wide?(hi==-2147483648LL?0:hi*100000):0);sprintf_s(key,64,"kind^%d",index);keyput(name,key,wide?(1+(lo==-2147483648LL?1:0)+(hi==-2147483648LL?2:0))*100000:0);}
static void make(const char* name,int n){keyput(name,"ver",200000);keyput(name,"gen",200000);keyput(name,"len",n*100000LL);keyput(name,"lo^num",n*100000LL);keyput(name,"hi^num",n*100000LL);keyput(name,"kind^num",n*100000LL);for(int i=0;i<n;i++)element(name,i,i*100000LL-12500,1);}
static int checks,failed;
static void check(const char* label,int good){checks++;if(!good){failed++;printf("FAIL %s\n",label);}}
static void test(const char* label,const char* name,int index,int wanted,long long raw,int count,int gen,int expectedgen){long long v=123;int n=-99,g=-99,s=Array64Group_Read(header,name,index,expectedgen,&v,&n,&g);check(label,s==wanted&&v==raw&&n==count&&g==gen);}
int main(void){long long v;int n,g,i;uint64_t random=1202612;unsigned char* before=malloc(sizeof(nodes));
 reset(0);header[40]=0;test("native_unallocated_empty","demo",0,0,123,-99,-99,-1);check("empty_native_array",NativeArray_Read(header,"demo",0,&v,&n)==0);
 memcpy(before,header,sizeof(header));Array64Group_Read(header,"demo",0,-1,&v,&n,&g);check("empty_no_mutation",!memcmp(before,header,sizeof(header)));
 header[40]=1;test("empty_invalid_spill","demo",0,-1,123,-99,-99,-1);header[40]=0;
 *(unsigned*)(header+32)=1;test("empty_invalid_count","demo",0,-1,123,-99,-99,-1);*(unsigned*)(header+32)=0;
 nodes[4]=1;test("empty_occupied_sentinel","demo",0,-1,123,-99,-99,-1);nodes[4]=0;
 *(void**)(header+24)=0;test("empty_null_table","demo",0,-1,123,-99,-99,-1);
 reset(255);test("absent","demo",0,0,123,-99,-99,-1);keyput("demo","lo^4095",900000);test("orphan","demo",0,-3,123,-99,-99,-1);
 reset(255);make("demo",0);test("empty","demo",0,2,123,0,2,-1);test("empty_stale","demo",0,-9,123,-99,-99,0);
 reset(255);make("demo",2);element("demo",0,LLONG_MIN,1);element("demo",1,LLONG_MAX,1);test("min","demo",0,1,LLONG_MIN,2,2,-1);test("max","demo",1,1,LLONG_MAX,2,2,2);
 test("negative","demo",-1,2,123,2,2,-1);test("upper","demo",2,2,123,2,2,-1);test("stale","demo",0,-9,123,-99,-99,0);
 element("demo",0,2147483648LL,1);test("low_escape","demo",0,1,2147483648LL,2,2,-1);
 element("demo",0,-9223372034707292160LL,1);test("both_escape","demo",0,1,-9223372034707292160LL,2,2,-1);
 keyput("demo","lo^0",100000);test("escape_requires_zero","demo",0,-8,123,-99,-99,-1);
 element("demo",0,250000,0);test("native_raw","demo",0,1,250000,2,2,-1);
 element("demo",0,LLONG_MAX,0);test("unsafe_native_raw","demo",0,-8,123,-99,-99,-1);element("demo",0,250000,0);
 keyput("demo","kind^1",500000);test("unrequested_bad_element","demo",0,-8,123,-99,-99,-1);
 reset(255);make("demo",1);keyput("demo","ver",100000);test("version","demo",0,-4,123,-99,-99,-1);
 keyput("demo","ver",200000);keyput("demo","gen",300000);test("odd","demo",0,-5,123,-99,-99,-1);
 keyput("demo","gen",200001);test("fraction_gen","demo",0,-5,123,-99,-99,-1);
 keyput("demo","gen",214748364700000LL);test("gen_overflow","demo",0,-5,123,-99,-99,-1);
 keyput("demo","gen",200000);keyput("demo","len",100001);test("fraction_length","demo",0,-6,123,-99,-99,-1);
 keyput("demo","len",409700000);test("length_limit","demo",0,-6,123,-99,-99,-1);
 keyput("demo","len",100000);keyput("demo","hi^num",0);test("columns","demo",0,-7,123,-99,-99,-1);
 reset(255);make("demo",1);keyput("demo","lo^0",1);test("fraction_component","demo",0,-8,123,-99,-99,-1);
 keyput("demo","lo^0",214748364800000LL);test("component_limit","demo",0,-8,123,-99,-99,-1);
 keyput("demo","lo^0",0);keyput("demo","kind^0",0);keyput("demo","hi^0",1);test("native_hi_not_zero","demo",0,-8,123,-99,-99,-1);
 reset(255);make("demo",1);keyput("demo","lo^9",0);test("extra_element","demo",0,-3,123,-99,-99,-1);
 reset(255);make("demo",1);keyput("demo","lo",0);test("base_collision","demo",0,-3,123,-99,-99,-1);
 reset(255);make("demo",1);keyput("demo","ver^0",0);test("manifest_array_collision","demo",0,-3,123,-99,-99,-1);
 reset(255);make("demo",1);make("demo_lo",1);test("namespace_boundary","demo",0,1,-12500,1,2,-1);test("suffix_name","demo_lo",0,1,-12500,1,2,-1);
 reset(255);keyput("demo","ver",100000);test("partial_manifest","demo",0,-2,123,-99,-99,-1);
 reset(255);make("abcdefghijklmnopqrst",1);test("long_name","abcdefghijklmnopqrst",0,1,-12500,1,2,-1);test("invalid_name","Global.demo",0,-1,123,-99,-99,-1);
 fault=1;test("unreadable","demo",0,-1,123,-99,-99,-1);fault=0;
 reset(255);make("demo",3);
 for(i=0;i<2048;i++){random^=random<<13;random^=random>>7;random^=random<<17;long long want=(long long)random;element("demo",i%3,want,1);int s=Array64Group_Read(header,"demo",i%3,-1,&v,&n,&g);check("random_signed64_roundtrip",s==1&&v==want&&n==3&&g==2);}
 memcpy(before,nodes,sizeof(nodes));for(i=0;i<20;i++)Array64Group_Read(header,"demo",0,-1,&v,&n,&g);check("no_mutation",!memcmp(before,nodes,sizeof(nodes)));
 reset(16383);make("demo",4096);test("4096_full_shape","demo",4095,1,409487500,4096,2,-1);
 free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+group+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(group.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_adapter':True}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
