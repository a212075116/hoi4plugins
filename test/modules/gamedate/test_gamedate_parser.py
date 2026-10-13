import argparse
import ast
import hashlib
import json
import pathlib
import random
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--optimization", choices=("Od", "O2"), default="O2")
args = parser.parse_args()
root = args.source_root.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
tree = ast.parse((ROOT / "test/modules/gamedate/test_gamedate_refactor.py").read_text(encoding="utf-8"))
fixture = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "fixture")
rng = random.Random(20261014)
values = [0, 1, 9999, 10000, 2147483646, 2147483647, 2147483648, 4294967295, 4294967296, 4294969232]
values += [rng.randrange(0, 2147483648) for _ in range(4000)]
values += [rng.randrange(2147483648, 10**40) for _ in range(4000)]
rows = []
for value in values:
    for suffix in ("", ".", "x"):
        digits = "0" * rng.randrange(0, 12) + str(value)
        text = digits + suffix
        result = value if value <= 2147483647 else -1
        rows.append(f"{text} {result} {len(digits) if result >= 0 else 0}\n")
rows += ["x -1 0\n", ". -1 0\n", "-1 -1 0\n", "+1 -1 0\n", "0" * 1000 + "1 1 1001\n", "9" * 1000 + " -1 0\n"]
inputs = "".join(rows).encode("ascii")
(output / "inputs.txt").write_bytes(inputs)
probe = r'''
 {
  FILE* input=fopen("inputs.txt","r");char token[2048];int wanted,advance,value,count=0,fault,oldCalls,accepted;
  unsigned char saved[sizeof(state)];const char* cursor;const char* original;
  if(!input)return 3;
  while(fscanf_s(input,"%2047s %d %d",token,(unsigned int)sizeof(token),&wanted,&advance)==3){
   cursor=token;value=ParseInt(&cursor);CHECK(value==wanted);CHECK(cursor==token+advance);++count;
  }
  fclose(input);
  fault=0;value=0;__try{value=ParseInt(NULL);}__except(EXCEPTION_EXECUTE_HANDLER){fault=1;}
  printf("null_cursor fault=%d value=%d\n",fault,value);CHECK(!fault&&value==-1);
  cursor=NULL;fault=0;value=0;__try{value=ParseInt(&cursor);}__except(EXCEPTION_EXECUTE_HANDLER){fault=1;}
  printf("null_text fault=%d value=%d\n",fault,value);CHECK(!fault&&value==-1&&cursor==NULL);
  cursor="";original=cursor;CHECK(ParseInt(&cursor)==-1&&cursor==original);
  {
   const char* bad[]={"4294969232.1.1","1936.4294967297.1","1936.1.4294967297","1936.1.1.4294967296","2147483648.1.1","999999999999999999999999999999.1.1"};
   for(i=0;i<6;++i){
    GameDate_SetRaw(oracle(1936,1,1,0));memcpy(saved,state,sizeof(state));oldCalls=uiCalls;
    accepted=GameDate_SetFromText(bad[i]);CHECK(!accepted);CHECK(!memcmp(saved,state,sizeof(state))&&uiCalls==oldCalls);
    printf("oversize[%d] accepted=%d atomic=%d\n",i,accepted,!memcmp(saved,state,sizeof(state))&&uiCalls==oldCalls);
   }
  }
  printf("parser_cases=%d\n",count);
 }
'''
anchor = ' printf("date=20000'
assert fixture.count(anchor) == 1
fixture = fixture.replace(anchor, probe + anchor)
sdk = root / "src/plugin/SDK_RVA"
for token, path in [("CONSOLE_HEADER", sdk / "console/console_cmd.h"), ("UI_SOURCE", sdk / "gamedate/gamedate_ui.c"), ("DATE_SOURCE", sdk / "gamedate/gamedate.c")]:
    fixture = fixture.replace(token, path.as_posix())
(output / "fixture.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
includes = [root / "src/carrier", sdk / "console", sdk / "gamedate", sdk / "hook"]
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /{args.optimization} ' + " ".join(f'/I"{p}"' for p in includes) + ' fixture.c /Fe:fixture.exe"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
record = dict(build=build, result=result, optimization=args.optimization, parser_cases=len(rows), input_sha256=hashlib.sha256(inputs).hexdigest(), scope="Production parser/date/UI sources, independent integer oracle, native dependencies mocked; SEH catches baseline null faults; no game calls")
(output / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
