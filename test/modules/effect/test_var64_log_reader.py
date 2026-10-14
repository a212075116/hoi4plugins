import argparse
import hashlib
import json
import pathlib
import random

from test_var64_text_refactor import VCVARS, execute, function


parser = argparse.ArgumentParser()
parser.add_argument("source", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
source, output = args.source.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
text = source.read_text(encoding="utf-8")
folder = source.parent
rng = random.Random(20261014)
rows = []
for i in range(6000):
    kind = i % 3
    raw = [250000, -250000, 1, -1, 0, 1234567890362500, -1234567890362500][i % 7] if i < 21 else rng.randrange(-9000000000000000000, 9000000000000000001) if kind == 0 else rng.randrange(-50000000000, 50000000001)
    integer = abs(raw) // 100000 * (-1 if raw < 0 else 1)
    fraction = raw - integer * 100000
    if kind == 0:
        bits = integer & ((1 << 64) - 1)
        low = bits & 0xFFFFFFFF
        high = bits >> 32
        low = (low - (1 << 32) if low >= (1 << 31) else low) * 100000
        high = (high - (1 << 32) if high >= (1 << 31) else high) * 100000
        stored_fraction = (fraction + 100000) * 100000
    else:
        low, high, stored_fraction = raw, rng.randrange(-3, 4) * 100000, 0
    debt_i, debt_f = (rng.randrange(-20, 21), rng.randrange(-99999, 100000)) if kind == 2 else (0, 0)
    wanted = raw + debt_i * 100000 + debt_f
    integer = abs(wanted) // 100000 * (-1 if wanted < 0 else 1)
    fraction = wanted - integer * 100000
    sign = "-" if wanted < 0 else ""
    formatted = sign + str(abs(integer)) + (("." + f"{abs(fraction):05d}".rstrip("0")) if fraction else "")
    bits = integer & ((1 << 64) - 1)
    rows.append(f"{kind} {low} {high} {stored_fraction} {debt_i} {debt_f} {wanted} {bits & 0xFFFFFFFF} {bits >> 32} {formatted}\n")
inputs = "".join(rows).encode("ascii")
(output / "inputs.txt").write_bytes(inputs)
fixture = r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "NAME_HEADER"
#include "DECIMAL_HEADER"
#include "MATH_HEADER"
static long long low,high,fraction;static int kind,resolve=1;
typedef struct{long long debtInt,debtFrac;}Var64DebtRecord;
static Var64DebtRecord debt;
static char output[256];static int reads,lookups;
static int Var64_ResolveGameVariable(void* self,void* ctx,long long* value,unsigned char** addr,char* name,int size){(void)self;(void)ctx;(void)value;if(!resolve)return 0;*addr=(unsigned char*)&low;strcpy_s(name,size,"demo");return 1;}
static unsigned char* Var64_ResolveAddressByName(void* self,void* ctx,const char* name){(void)self;(void)ctx;++lookups;return (unsigned char*)(strstr(name,"var64f")?&fraction:&high);}
static int Var64_IsStored64(void* self,void* ctx,const char* name){(void)self;(void)ctx;(void)name;++reads;return kind==0;}
static Var64DebtRecord* Var64_FindDebt(void* self,void* ctx,const char* name){(void)self;(void)ctx;(void)name;return kind==2?&debt:NULL;}
void Plugin_Log(const char* fmt,...){va_list args;va_start(args,fmt);vsnprintf(output,sizeof(output),fmt,args);va_end(args);}
READ_SPLIT
READ_TRUE
DO_LOG
static int checks,failed;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL case=%d line=%d\n",cases,__LINE__);}}while(0)
int main(void){
 FILE* f=fopen("inputs.txt","r");long long want,result;unsigned int lo,hi;char expected[64],message[256];int cases=0,marked=0,markedFailed=0;
 if(!f)return 2;
 while(fscanf_s(f,"%d %lld %lld %lld %lld %lld %lld %u %u %63s",&kind,&low,&high,&fraction,&debt.debtInt,&debt.debtFrac,&want,&lo,&hi,expected,(unsigned int)sizeof(expected))==10){
  long long before[5]={low,high,fraction,debt.debtInt,debt.debtFrac};int prior=failed;
  reads=lookups=0;result=Var64_DoLogVariable64((void*)1,(void*)2);
  CHECK(result==want);sprintf_s(message,sizeof(message),"[var64] log_variable64 demo = %s (lo=%u hi=%u)",expected,lo,hi);CHECK(!strcmp(output,message));
  CHECK(low==before[0]&&high==before[1]&&fraction==before[2]&&debt.debtInt==before[3]&&debt.debtFrac==before[4]);
  if(kind==0){++marked;markedFailed+=failed!=prior;}
  ++cases;
 }
 fclose(f);resolve=0;CHECK(Var64_DoLogVariable64((void*)1,(void*)2)==0);CHECK(!strcmp(output,"[var64] log_variable64 failed to resolve"));
 printf("log_cases=%d marked_cases=%d marked_failed=%d checks=%d failed=%d;actual log/reader/format,controlled scope/debt,no writes\n",cases,marked,markedFailed,checks,failed);return failed?1:0;
}
'''
for token, value in [("NAME_HEADER", (folder / "variable64_name.h").as_posix()), ("DECIMAL_HEADER", (folder / "variable64_decimal.h").as_posix()), ("MATH_HEADER", (folder / "variable64_math.h").as_posix()), ("READ_SPLIT", function(text, "Var64_LoadSplit64")), ("READ_TRUE", function(text, "Var64_ReadTrueRaw")), ("DO_LOG", function(text, "Var64_DoLogVariable64"))]:
    fixture = fixture.replace(token, value)
(output / "fixture.c").write_text(fixture, encoding="ascii")
command = 'cmd /d /s /c "' + f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe' + '"'
p, build = execute(command, output)
result = build
if p.returncode == 0:
    p, result = execute([str(output / "fixture.exe")], output)
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, input_sha256=hashlib.sha256(inputs).hexdigest(), scope="Actual log,split,true reader andformatter;scope/debt lookup dependencies modeled;read-only slot invariant andmarked compatibility"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(p.returncode)
