import argparse
import hashlib
import json
import pathlib
import random
import re
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
folder = root / "src/plugin/SDK_RVA/variable64"
def function(text, name):
    match = re.search(r"^static [^;\n]+\b" + name + r"\([^;]+?\n\{", text, re.M)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[match.start():end] + "\n"
if (folder / "array64_wire.h").exists():
    source = f'#include "{(folder / "array64_wire.h").as_posix()}"\n#include "{(folder / "array64_owner_key.h").as_posix()}"\n'
else:
    durable = (folder / "array64_durable_snapshot.c").read_text(encoding="utf-8")
    journal = (folder / "array64_shape_journal.c").read_text(encoding="utf-8")
    source = "".join(function(durable, name) for name in ("ad_get", "ad_put", "ad_hash"))
    expression = re.search(r"snapshot->parts\[i\]\[j\]=([^;]+);", durable).group(1)
    source += "static long long ad_i64(const unsigned char* p){unsigned long long bits=ad_get(p,8);return " + expression + ";}\n"
    source += function(journal, "aj_i32").replace("aj_i32", "ad_i32")
    source += function((folder / "array64_shape_transaction.c").read_text(encoding="utf-8"), "as_owner_key")
rng = random.Random(20261015)
rows = []
for i in range(8000):
    data = bytes(rng.randrange(256) for _ in range(16)) if i > 4 else bytes([0, 0x7F, 0x80, 0xFF, 1][i] for _ in range(16))
    width, length = i % 9, i % 17
    value = int.from_bytes(data[:width], "little")
    signed64 = int.from_bytes(data[:8], "little", signed=True)
    signed32 = int.from_bytes(data[:4], "little", signed=True)
    checksum = 14695981039346656037
    for byte in data[:length]:
        checksum = ((checksum ^ byte) * 1099511628211) & ((1 << 64) - 1)
    rows.append(f"{data.hex()} {width} {length} {value} {signed64} {signed32} {checksum}\n")
inputs = "".join(rows).encode("ascii")
(output / "inputs.txt").write_bytes(inputs)
keys = []
for i in range(500):
    name = chr(97 + i % 26) + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789_") for _ in range(i % 20))
    for index in range(8):
        keys.append(f"{name} {index} __v64o_{name}_{'b' if index < 4 else 'i'}{index % 4}\n")
(output / "keys.txt").write_text("".join(keys), encoding="ascii")
main = r'''
#include <stdio.h>
#include <string.h>
static int checks,failed;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL line=%d\n",__LINE__);}}while(0)
static int nibble(char c){return c>='a'?c-'a'+10:c-'0';}
int main(void){
 FILE* f=fopen("inputs.txt","r");char hex[33],name[21],expected[41],key[48];unsigned char data[16],out[16];
 unsigned int n,length;unsigned long long value,hash;long long signed64;int signed32,index,i,cases=0,keyCases=0;
 if(!f)return 2;
 while(fscanf_s(f,"%32s %u %u %llu %lld %d %llu",hex,(unsigned int)sizeof(hex),&n,&length,&value,&signed64,&signed32,&hash)==7){
  for(i=0;i<16;++i)data[i]=(unsigned char)(16*nibble(hex[2*i])+nibble(hex[2*i+1]));
  CHECK(ad_get(data,(int)n)==value);CHECK(ad_i64(data)==signed64);CHECK(ad_i32(data)==signed32);CHECK(ad_hash(data,length)==hash);
  memset(out,0xA5,sizeof(out));ad_put(out,value,(int)n);
  for(i=0;i<16;++i)CHECK(out[i]==(i<(int)n?data[i]:0xA5));++cases;
 }
 fclose(f);f=fopen("keys.txt","r");if(!f)return 3;
 while(fscanf_s(f,"%20s %d %40s",name,(unsigned int)sizeof(name),&index,expected,(unsigned int)sizeof(expected))==3){
  memset(key,0xA5,sizeof(key));as_owner_key(key,name,index);CHECK(!strcmp(key,expected));CHECK((unsigned char)key[strlen(expected)+1]==0xA5);++keyCases;
 }
 fclose(f);printf("wire_cases=%d owner_keys=%d checks=%d failed=%d\n",cases,keyCases,checks,failed);return failed?1:0;
}
'''
(output / "fixture.c").write_text(source + main, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /TC /O2 fixture.c /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, input_sha256=hashlib.sha256(inputs).hexdigest(), scope="Production helpers or baseline textual inline projections; independent endian/FNV/signed/key oracle; full imports/journals tested separately"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
