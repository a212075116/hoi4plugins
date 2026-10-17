import argparse
import ast
import hashlib
import json
import math
import pathlib
import random
import re
import struct
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--optimization", choices=("Od", "O2"), default="O2")
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
tree = ast.parse((ROOT / "test/modules/gamedate/test_gamedate_refactor.py").read_text(encoding="utf-8"))
fixture = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "fixture")
sdk = root / "src/plugin/SDK_RVA"
source = (sdk / "effect/effect_gamedate.c").read_text(encoding="utf-8")
match = re.search(r"^static void RunAdd\([^;]+?\n\{", source, re.M)
end, depth = match.end(), 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
adapter = f'#include "{(sdk / "effect/effect_reg.h").as_posix()}"\n'
adapter += "static float operand; static int flushCalls, g_dateEffectExecCount;\nfloat Effect_ParamFloat(void* s,void* c){(void)s;(void)c;return operand;}\nvoid Effect_FlushPendingTooltip(void){++flushCalls;}\n"
adapter += source[match.start():end] + "\n"
fixture = fixture.replace("int main(void){", adapter + "int main(void){")
months = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
def encode(y, m, d, h):
    return 43800000 + (365 * y + sum(months[:m - 1]) + d - 1) * 24 + h
def decode(raw):
    days, h = divmod(raw - 43800000, 24)
    y, remaining = divmod(days, 365)
    m = 1
    while remaining >= months[m - 1]:
        remaining -= months[m - 1]
        m += 1
    return y, m, remaining + 1, h
def add(raw, unit, delta):
    if unit == 1:
        y, m, d, h = decode(raw)
        y, m = divmod(y * 12 + m - 1 + delta, 12)
        y = min(9999, max(1, y))
        return encode(y, m + 1, min(d, months[m]), h)
    return raw + delta * {0: 8760, 2: 24, 3: 1}[unit]
def legacy_defined(raw, unit, delta, result):
    if unit == 1:
        return int(-2147483648 <= decode(raw)[1] + delta <= 2147483647)
    scaled = delta * {0: 8760, 2: 24, 3: 1}[unit]
    return int(-2147483648 <= scaled <= 2147483647 and -2103683648 <= result <= 2147483647)
rng = random.Random(20261014)
rows = []
for i in range(12000):
    if i < 6000:
        y, m = rng.randrange(1, 10000), rng.randrange(1, 13)
        raw = encode(y, m, rng.randrange(1, months[m - 1] + 1), rng.randrange(24))
        unit, delta = 1, rng.randrange(-100000, 100001)
    else:
        raw, unit, delta = rng.randrange(2147483648), (0, 2, 3)[i % 3], rng.randrange(-300000, 300001)
    result = add(raw, unit, delta)
    ok = int(-2147483648 <= result <= 2147483647)
    parts = decode(result) if ok else (0, 0, 0, 0)
    rows.append(f"{raw} {unit} {delta} {ok} {result if ok else 0} " + " ".join(map(str, parts)) + f" {legacy_defined(raw, unit, delta, result)}\n")
for unit, delta in [(1, -2147483648), (1, 2147483635), (1, 2147483647), (0, 2147483647), (2, -2147483648), (3, 2147483647), (3, -2147483648)]:
    raw = encode(1936, 1, 31, 12) if unit != 3 else 0
    result = add(raw, unit, delta)
    ok = int(-2147483648 <= result <= 2147483647)
    rows.append(f"{raw} {unit} {delta} {ok} {result if ok else 0} " + " ".join(map(str, decode(result) if ok else (0, 0, 0, 0))) + f" {legacy_defined(raw, unit, delta, result)}\n")
inputs = "".join(rows).encode("ascii")
(output / "inputs.txt").write_bytes(inputs)
float_rows = []
for value in [float("nan"), float("inf"), -float("inf"), 2147483648.0, -2147483648.0, 3.402823466e38, -3.402823466e38, 2147483520.0, -0.75, 0.75, 1.9, -1.9, 100000.0, -100000.0]:
    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    value = struct.unpack("<f", struct.pack("<I", bits))[0]
    for unit in range(4):
        raw = encode(1936, 1, 31, 12)
        legal = math.isfinite(value) and -2147483648 <= value <= 2147483647
        result = add(raw, unit, math.trunc(value)) if legal else 0
        ok = int(legal and -2147483648 <= result <= 2147483647)
        float_rows.append(f"{bits} {unit} {ok} {result if ok else raw}\n")
(output / "floats.txt").write_text("".join(float_rows), encoding="ascii")
probe = r'''
 {
  FILE* input=fopen("inputs.txt","r");int raw,unit,delta,ok,wanted,ey,em,ed,eh,result,oldUi,yy,mm,dd,hh,count=0,defined,prior,compat=0,compatFailed=0,q;
  unsigned long long compatHash=1469598103934665603ULL;
  unsigned char saved[sizeof(state)];unsigned int bits;int oldFlush,oldExec;
  if(!input)return 3;
  while(fscanf_s(input,"%d %d %d %d %d %d %d %d %d %d",&raw,&unit,&delta,&ok,&wanted,&ey,&em,&ed,&eh,&defined)==10){
   GameDate_SetRaw(raw);memcpy(saved,state,sizeof(state));oldUi=uiCalls;result=GameDate_Add(unit,delta);
   prior=failures;CHECK(result==ok);
   if(ok){CHECK(*(int*)(state+OFF_GD_RAW)==wanted&&uiCalls==oldUi+1);GameDate_DecodeRaw(wanted,&yy,&mm,&dd,&hh);CHECK(yy==ey&&mm==em&&dd==ed&&hh==eh);CHECK(*(int*)(state+OFF_GD_YEAR)==ey&&*(int*)(state+OFF_GD_MONTH0)==em-1&&*(int*)(state+OFF_GD_DAY)==ed);}
   else CHECK(!memcmp(saved,state,sizeof(state))&&uiCalls==oldUi);
   if(defined){++compat;compatFailed+=failures!=prior;for(q=0;q<(int)sizeof(state);++q)compatHash=(compatHash^state[q])*1099511628211ULL;compatHash=(compatHash^(unsigned int)(uiCalls-oldUi))*1099511628211ULL;}
   ++count;
  }
  fclose(input);printf("arithmetic_cases=%d compatibility_cases=%d compatibility_failed=%d compatibility_hash=%llu\n",count,compat,compatFailed,compatHash);input=fopen("floats.txt","r");if(!input)return 4;count=0;
  while(fscanf_s(input,"%u %d %d %d",&bits,&unit,&ok,&wanted)==4){
   GameDate_SetRaw(oracle(1936,1,31,12));memcpy(saved,state,sizeof(state));oldUi=uiCalls;oldFlush=flushCalls;oldExec=g_dateEffectExecCount;
   memcpy(&operand,&bits,4);RunAdd(effect,NULL,unit,"fixture");
   CHECK(flushCalls==oldFlush+1&&g_dateEffectExecCount==oldExec+1);
   if(ok)CHECK(*(int*)(state+OFF_GD_RAW)==wanted&&uiCalls==oldUi+1);
   else CHECK(!memcmp(saved,state,sizeof(state))&&uiCalls==oldUi);
   ++count;
  }
  fclose(input);printf("effect_float_cases=%d\n",count);
 }
'''
fixture = fixture.replace(' printf("date=20000', probe + ' printf("date=20000')
for token, path in [("CONSOLE_HEADER", sdk / "console/console_cmd.h"), ("UI_SOURCE", sdk / "gamedate/gamedate_ui.c"), ("DATE_SOURCE", sdk / "gamedate/gamedate.c")]:
    fixture = fixture.replace(token, path.as_posix())
if "NativeAdapter_Symbol" in (sdk / "gamedate/gamedate.h").read_text(encoding="utf-8"):
    fixture = fixture.replace('#include <string.h>\n', '#include <string.h>\n#include "' + (root / "test/lib/native_symbols_fixture.h").as_posix() + '"\n', 1)
(output / "fixture.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
includes = [root / "src/carrier", sdk / "console", sdk / "gamedate", sdk / "hook"]
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /{args.optimization} ' + " ".join(f'/I"{p}"' for p in includes) + ' fixture.c /Fe:fixture.exe"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, optimization=args.optimization, arithmetic_cases=len(rows), float_cases=len(float_rows), input_sha256=hashlib.sha256(inputs).hexdigest(), scope="Production date/UI and actual Effect RunAdd; independent Python integer/calendar oracle; native dependencies mocked; no game calls"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
