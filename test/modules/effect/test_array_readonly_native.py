import hashlib, json, pathlib, subprocess, sys
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
static unsigned char header[48],nodes[16384*48];
static char heapname[128];
static int fault=0;
int na_read_memory(const void* p,void* out,unsigned long long n){
 uintptr_t a=(uintptr_t)p,h=(uintptr_t)header,b=(uintptr_t)nodes;
 if(fault||!p||n>4096)return 0;
 if((a>=h&&a-h<=sizeof(header)&&n<=sizeof(header)-(a-h)) ||
    (a>=b&&a-b<=sizeof(nodes)&&n<=sizeof(nodes)-(a-b)) ||
    (a>=(uintptr_t)heapname&&a-(uintptr_t)heapname<=sizeof(heapname)&&n<=sizeof(heapname)-(a-(uintptr_t)heapname))) {memcpy(out,p,(size_t)n);return 1;}
 return 0;
}
'''
main=r'''
static unsigned hash(const char* n){unsigned h=2166136261u;while(*n)h=(h^(unsigned char)*n++)*16777619u;return h;}
static void reset(void){memset(header,0,sizeof(header));memset(nodes,0,sizeof(nodes));*(void**)(header+24)=nodes;*(unsigned*)(header+36)=8191;header[40]=32;fault=0;}
static void add(const char* n,long long raw){unsigned h=hash(n);unsigned char entry[48]={0},temp[48];unsigned char* p=nodes+(h&8191)*48;
 *(unsigned*)entry=h;entry[4]=1;memcpy(entry+8,n,strlen(n));*(uint64_t*)(entry+24)=strlen(n);*(uint64_t*)(entry+32)=15;*(long long*)(entry+40)=raw;
 while(p[4]){if(p[4]<entry[4]){memcpy(temp,p,48);memcpy(p,entry,48);memcpy(entry,temp,48);}p+=48;entry[4]++;}memcpy(p,entry,48);
}
static int checks=0,failed=0;
static void check(const char* label,int condition){checks++;if(!condition){failed++;printf("FAIL %s\n",label);}}
static void test(const char* label,const char* name,int index,int expected,int count,long long raw){long long v=123;int c=-99;int s=NativeArray_Read(header,name,index,&v,&c);check(label,s==expected&&c==count&&v==raw);}
int main(void){char key[32],collision[32];int i;unsigned char* before=malloc(sizeof(nodes));long long raw;int count;
 reset();test("absent","arr",0,0,-99,123);
 add("arr",LLONG_MAX);add("arr_var64h",123);add("arr_var64f",123);test("scalar_is_not_array","arr",0,0,-99,123);
 add("arr^num",0);test("empty","arr",0,2,0,123);test("negative_empty","arr",-1,2,0,123);
 reset();add("arr^num",200000);add("arr^0",250000);add("arr^1",-12500);
 test("index0","arr",0,1,2,250000);test("index1","arr",1,1,2,-12500);test("upper","arr",2,2,2,123);test("negative","arr",-1,2,2,123);
 memcpy(before,nodes,sizeof(nodes));for(i=0;i<2000;i++)NativeArray_Read(header,"missing",0,&raw,&count);check("missing_read_no_mutation",!memcmp(before,nodes,sizeof(nodes)));
 fault=1;test("unreadable","arr",0,-1,-99,123);fault=0;
 *(unsigned*)(header+36)=8190;test("invalid_mask","arr",0,-1,-99,123);
 reset();add("arr^num",100001);test("fraction_count","arr",0,-2,-99,123);
 reset();add("arr^num",-100000);test("negative_count","arr",0,-2,-99,123);
 reset();add("arr^num",409700000);test("limit_count","arr",0,-2,-99,123);
 reset();add("arr^num",100000);test("missing_element","arr",0,-3,-99,123);
 reset();add("arr^num",409600000);add("arr^4095",LLONG_MIN);test("last_limit_min","arr",4095,1,4096,LLONG_MIN);test("last_limit_oob","arr",4096,2,4096,123);
 test("invalid_scoped_name","global.arr",0,-1,-99,123);test("invalid_index_name","arr^0",0,-1,-99,123);
 reset();add("arr^num",100000);add("arr^0",LLONG_MAX);test("raw_max","arr",0,1,1,LLONG_MAX);
 reset();{const char* longkey="__v64a_abcdefghijklmnopqrst_kind^num";unsigned char* p=nodes+(hash(longkey)&8191)*48;
 strcpy_s(heapname,sizeof(heapname),longkey);*(unsigned*)p=hash(longkey);p[4]=1;*(void**)(p+8)=heapname;*(uint64_t*)(p+24)=strlen(longkey);*(uint64_t*)(p+32)=63;*(long long*)(p+40)=0;
 test("heap_long_name","__v64a_abcdefghijklmnopqrst_kind",0,2,0,123);
 *(void**)(p+8)=(void*)1;test("bad_heap_pointer","__v64a_abcdefghijklmnopqrst_kind",0,-1,-99,123);}
 reset();for(i=0;i<500000;i++){sprintf_s(key,sizeof(key),"spill%d",i);if((hash(key)&8191)==8191)break;}check("spill_name_found",i<500000);strcpy_s(collision,sizeof(collision),key);
 for(i++;i<1000000;i++){sprintf_s(key,sizeof(key),"spill%d",i);if((hash(key)&8191)==8191)break;}check("spill_collision_found",i<1000000);
 add(collision,10);add(key,20);check("continuous_not_modulo_wrap",na_lookup(header,key,&raw)==1&&raw==20);
 reset();add("arr^num",409600000);
 for(i=0;i<4096;i++){sprintf_s(key,sizeof(key),"arr^%d",i);add(key,(long long)i*100000-12500);}
 memcpy(before,nodes,sizeof(nodes));for(i=0;i<4096;i++){int s=NativeArray_Read(header,"arr",i,&raw,&count);check("many_elements",s==1&&count==4096&&raw==(long long)i*100000-12500);}
 check("full_read_no_mutation",!memcmp(before,nodes,sizeof(nodes)));
 {unsigned char* p=nodes+(hash("arr^0")&8191)*48;*(uint64_t*)(p+32)=2;test("malformed_name_capacity","arr",0,-1,-99,123);}
 free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+source.read_text(encoding='utf-8')+main,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
result={'command':sys.argv,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'memory_adapter':'bounded synthetic native-layout fixture; real C backend, not game runtime'}
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(p.returncode)
