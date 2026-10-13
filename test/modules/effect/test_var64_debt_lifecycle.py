"""Exercise real debt-table lifecycle with deterministic allocation failures and an oracle."""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path

from test_var64_text_refactor import VCVARS, execute


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();source=args.source.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    text=source.read_text(encoding='utf-8-sig');piece=source.parent/'variable64_debt.inc'
    code='#include "'+piece.as_posix()+'"\n' if piece.exists() else text[text.index('#define VAR64_DEBT_MAX'):text.index('static int Var64_ReadOperandLiteralAt(')]
    fixture=r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdarg.h>
static int flags,containers,heaps,allocations,reallocations;
static size_t allocatedBytes;static char logText[256];
static void* Var64_Container(void* self,void* ctx){(void)self;++containers;return flags&2?NULL:ctx;}
static HANDLE WINAPI ProcessHeap(void){++heaps;return (HANDLE)1;}
static void* WINAPI Allocate(HANDLE heap,DWORD f,SIZE_T size){(void)heap;++allocations;if(f!=HEAP_ZERO_MEMORY)exit(3);if(flags&1)return NULL;allocatedBytes=size;return calloc(1,size);}
static void* WINAPI Reallocate(HANDLE heap,DWORD f,void* old,SIZE_T size){void* p;(void)heap;++reallocations;if(f!=HEAP_ZERO_MEMORY)exit(3);if(flags&1)return NULL;p=calloc(1,size);if(!p)exit(4);memcpy(p,old,allocatedBytes);free(old);allocatedBytes=size;return p;}
static void Plugin_Log(const char* fmt,...){va_list a;va_start(a,fmt);vsnprintf(logText,sizeof(logText),fmt,a);va_end(a);}
#define GetProcessHeap ProcessHeap
#define HeapAlloc Allocate
#define HeapReAlloc Reallocate
DEBT_CODE
static const char* name(int key,char* buffer,size_t size){if(key==0)return NULL;if(key==1)return "";if(key==2)return "same";if(key==3)return "abcdefghijklmnopqrstuvwxyz0123456";if(key==4)return "x";if(key==5)return "abcdefghij";sprintf_s(buffer,size,"name%d",key);return buffer;}
static unsigned long long hash(const void* data,size_t size){const unsigned char* p=data;size_t i;unsigned long long h=14695981039346656037ULL;for(i=0;i<size;++i){h^=p[i];h*=1099511628211ULL;}return h;}
static void hex(const char* text){size_t i;if(!*text){putchar('-');return;}for(i=0;text[i];++i)printf("%02x",(unsigned char)text[i]);}
int main(void){int op,owner,key,index;long long a,b;char named[40];
 if(sizeof(Var64DebtRecord)!=72||offsetof(Var64DebtRecord,container)!=40||offsetof(Var64DebtRecord,debtInt)!=48||offsetof(Var64DebtRecord,active)!=64)return 2;
 while(scanf_s("%d %d %d %d %d %lld %lld",&op,&owner,&key,&index,&flags,&a,&b)==7){
  const char* n=name(key,named,sizeof(named));Var64DebtRecord* record=NULL;uintptr_t before=(uintptr_t)g_var64Debts;int result=-2,i,active=0;
  containers=heaps=allocations=reallocations=0;logText[0]=0;
  if(op==0){record=Var64_NewDebt((void*)1,(void*)(uintptr_t)owner,n);result=record?(int)(record-g_var64Debts):-1;}
  else if(op==1){record=Var64_FindDebt((void*)1,(void*)(uintptr_t)owner,n);result=record?(int)(record-g_var64Debts):-1;}
  else if(op==2)Var64_ClearDebt(index>=0&&index<g_var64DebtCapacity?&g_var64Debts[index]:NULL);
  else if(op==3)Var64_ResetDebtForSet((void*)1,(void*)(uintptr_t)owner,n);
  else if(op==4){if(index>=0&&index<g_var64DebtCapacity){g_var64Debts[index].debtInt=a;g_var64Debts[index].debtFrac=b;result=index;}else result=-1;}
  else return 5;
  for(i=0;i<g_var64DebtCapacity;++i)active+=g_var64Debts[i].active!=0;
  printf("%d %d %d %d %d %d %d %d %llu ",result,g_var64DebtCapacity,active,(uintptr_t)g_var64Debts!=before,containers,heaps,allocations,reallocations,hash(g_var64Debts,g_var64DebtCapacity*sizeof(*g_var64Debts)));hex(logText);puts("");
 }
 free(g_var64Debts);return 0;
}
'''.replace('DEBT_CODE',code)
    (output/'fixture.c').write_text(fixture,encoding='ascii')
    command=f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process,build=execute('cmd /d /s /c "'+command+'"',output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build,indent=2),encoding='utf-8');print(json.dumps(build,indent=2));return build_process.returncode
    cases=[(1,1,2,0,0,0,0),(0,1,2,0,1,0,0),(0,1,0,0,0,0,0),(0,0,2,0,0,0,0),(0,1,2,0,0,0,0),(0,2,2,0,0,0,0),
           (4,0,0,0,0,3000000000,25000),(4,0,0,1,0,-3000000000,-25000),(1,1,2,0,0,0,0),(1,2,2,0,0,0,0),(3,1,2,0,0,0,0),(1,2,2,0,0,0,0),
           (0,3,3,0,0,0,0),(0,3,3,0,0,0,0),(2,0,0,0,0,0,0),(0,4,4,0,0,0,0)]
    # Fill all slots, fail one growth, retry growth, then reuse slots without shrinking.
    cases.extend((0,owner%8+1,owner+6,0,0,0,0) for owner in range(61))
    cases.extend([(0,1,99,0,1,0,0),(0,1,99,0,0,0,0),(0,1,99,0,0,0,0),(1,1,99,0,0,0,0),(2,0,0,1,0,0,0),(0,8,1,0,0,0,0)])
    randomizer=random.Random(20261016)
    for _ in range(10000):cases.append((randomizer.choices([0,1,2,3,4],[3,4,3,3,2])[0],randomizer.randrange(9),randomizer.randrange(40),randomizer.randrange(-1,300),randomizer.randrange(4),randomizer.randint(-2**32,2**32),randomizer.randint(-99999,99999)))
    data=bytearray();capacity=0;expected=[]
    def name(key):return None if key==0 else '' if key==1 else 'same' if key==2 else 'abcdefghijklmnopqrstuvwxyz0123456' if key==3 else 'x' if key==4 else 'abcdefghij' if key==5 else 'name%d'%key
    def find(owner,text):
        for i in range(capacity):
            offset=i*72
            if struct.unpack_from('<i',data,offset+64)[0] and struct.unpack_from('<Q',data,offset+40)[0]==owner and bytes(data[offset:offset+40]).split(b'\0')[0].decode()==text:return i
        return -1
    def clear(index):
        if 0<=index<capacity:
            offset=index*72;data[offset]=0;struct.pack_into('<qqi',data,offset+48,0,0,0)
    for op,owner,key,index,flag,a,b in cases:
        text=name(key);result=-2;changed=containers=heaps=allocations=reallocations=0;log='';container=0 if flag&2 else owner
        if op==0:
            containers=1;result=-1
            if text is not None and container:
                index=next((i for i in range(capacity) if struct.unpack_from('<i',data,i*72+64)[0]==0),capacity)
                if index==capacity:
                    heaps=1;allocations=int(capacity==0);reallocations=int(capacity!=0)
                    if flag&1:log='[var64] cannot allocate debt record [%s]'%text
                    else:
                        next_capacity=64 if capacity==0 else capacity*2;data.extend(bytes((next_capacity-capacity)*72));capacity=next_capacity;changed=1
                if not log:
                    offset=index*72;encoded=text.encode()+b'\0';data[offset:offset+len(encoded)]=encoded;struct.pack_into('<Qqqi',data,offset+40,container,0,0,1);result=index
        elif op in [1,3]:
            result=-1 if op==1 else -2
            if text is not None and capacity:
                containers=1
                if container:
                    located=find(container,text)
                    if op==1:result=located
                    else:clear(located)
        elif op==2:clear(index)
        elif op==4:
            result=index if 0<=index<capacity else -1
            if result>=0:struct.pack_into('<qq',data,index*72+48,a,b)
        active=sum(struct.unpack_from('<i',data,i*72+64)[0]!=0 for i in range(capacity));checksum=14695981039346656037
        for byte in data:checksum=((checksum^byte)*1099511628211)&0xffffffffffffffff
        expected.append('%d %d %d %d %d %d %d %d %d %s'%(result,capacity,active,changed,containers,heaps,allocations,reallocations,checksum,log.encode().hex() if log else '-'))
    inputs=''.join('%d %d %d %d %d %d %d\n'%case for case in cases).encode();(output/'inputs.txt').write_bytes(inputs)
    process,result=execute([str(output/'fixture.exe')],output,inputs);(output/'stdout.txt').write_bytes(process.stdout);(output/'stderr.txt').write_bytes(process.stderr);observed=process.stdout.decode('ascii').splitlines()
    failures=[dict(index=i,input=cases[i],expected=row,observed=observed[i] if i<len(observed) else None) for i,row in enumerate(expected) if i>=len(observed) or observed[i]!=row]
    result.pop('stdout');result.update(stdout_file=str(output/'stdout.txt'),stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),seed=20261016,cases=len(cases),passed=len(cases)-len(failures),failures=failures,build=build,result=result,
                input_sha256=hashlib.sha256(inputs).hexdigest(),exit=int(bool(failures) or process.returncode!=0 or len(observed)!=len(cases)),scope='Real lifecycle functions, modeled container resolver and relocating zeroing heap; independent Python byte-level state/trace oracle; no game process')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='failures'},ensure_ascii=False,indent=2));return record['exit']


if __name__=='__main__':
    raise SystemExit(main())
