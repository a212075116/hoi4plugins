"""Compile the actual saturation helpers and compare with Python integer oracles."""
import json,pathlib,random,subprocess,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=pathlib.Path(__file__).resolve().parents[3]
source=pathlib.Path(sys.argv[1]).resolve()
out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=source.read_text(encoding='utf-8-sig')
math_header=source.parent/'variable64_math.h'
code=('#include "'+math_header.as_posix()+'"\n') if math_header.exists() else s[s.index('static long long Var64_SaturatingAdd('):s.index('static int Var64_TryDebtArithmetic(')]
prefix='#include <stdio.h>\n#include <intrin.h>\n#define VAR64_TRUE_CLAMP 9223372036854775807LL\n#define VAR64_FRAC_SCALE 100000LL\n#define VAR64_OP_ADD 0\n#define VAR64_OP_SUB 1\n#define VAR64_OP_MUL 2\n#define VAR64_OP_DIV 3\n'
main='int main(void){long long a,b,result;int op;while(scanf_s("%lld %lld %d",&a,&b,&op)==3){int ok=Var64_CalculateRaw(a,b,op,&result);if(ok)printf("%lld\\n",result);else printf("ZERO\\n");}return 0;}\n'
(out/'fixture.c').write_text(prefix+code+main,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
assert p.returncode==0,(out/'compile.stdout.txt').read_text(errors='replace')
M=2**63-1
values=[-M-1,-M,-M+1,-2**32,-100000,-1,0,1,99999,100000,2**32,M-1,M]
cases=[(a,b,op) for a in values for b in values for op in range(4)]
rng=random.Random(12026)
cases.extend((rng.randint(-M,M),rng.randint(-M,M),rng.randrange(4)) for _ in range(10000))
data=''.join('%d %d %d\n'%c for c in cases)
def oracle(a,b,op):
    if op==3 and b==0:return 'ZERO'
    if op==0:n=a+b
    elif op==1:n=a-b
    elif op==2:n=(abs(a*b)//100000)*(1 if a*b>=0 else -1)
    else:n=(abs(a*100000)//abs(b))*(1 if a*b>=0 else -1)
    return str(max(-M,min(M,n)))
p=subprocess.run([str(out/'fixture.exe')],input=data.encode('ascii'),capture_output=True)
actual=p.stdout.decode('ascii').splitlines()
failed=[{'input':c,'expected':oracle(*c),'actual':actual[i] if i<len(actual) else None} for i,c in enumerate(cases) if i>=len(actual) or oracle(*c)!=actual[i]]
(out/'inputs.txt').write_text(data,encoding='ascii')
(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
result={'checks':len(cases),'passed':len(cases)-len(failed),'failed':failed,'exit':p.returncode,'seed':12026}
(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2));raise SystemExit(bool(failed) or p.returncode)
