"""Exercise the actual read-only three-slot decoder, including malformed overflow metadata."""
import ast,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
source=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=source.read_text(encoding='utf-8-sig')
name_header=source.parent/'variable64_name.h'
if name_header.exists():
    s=s.replace('#include "variable64_name.h"',name_header.read_text(encoding='utf-8-sig'))
tree=ast.parse((ROOT/'test/modules/effect/test_var64_identity.py').read_text(encoding='utf-8'))
parts={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and n.targets[0].id in ['prefix','main']}
def fn(name):
 p=s.index(name+'(');start=s.rfind('static ',0,p);a=s.index('{',p);i=a+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]+'\n'
code=(fn('Var64_MakePartName') if 'static int Var64_MakePartName(' in s else '')+''.join(fn(n) for n in ['Var64_Fnv1a','Var64_LookupInScope','Var64_MakeHighPartName','Var64_MakeFracPartName','Var64_ReadStoredIn'])
add=parts['main'].split('static void triple(')[0]
main=r'''
int main(void){long long lo,hi,frac;while(scanf_s("%lld %lld %lld",&lo,&hi,&frac)==3){Scope c;long long raw=333;int ok;init(&c);add(&c,"value",lo);add(&c,"value_var64h",hi);add(&c,"value_var64f",frac);ok=Var64_ReadStoredIn(&c,"value",&raw);printf("%d %lld\n",ok,raw);free(*(void**)(c.b+24));}return 0;}
'''
(out/'fixture.c').write_text(parts['prefix']+code+add+main,encoding='ascii')
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W3 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_text(encoding='mbcs',errors='replace'));raise SystemExit(p.returncode)
M=2**63-1;rng=random.Random(1202610);raws=[-M-1,-M,-1,0,1,M-1,M]+[rng.randint(-M-1,M) for _ in range(2000)]
cases=[]
def signed32(v):return (v+2**31)%2**32-2**31
def put(integer,fraction):
 raw=integer*100000+fraction;ok=-M-1<=raw<=M
 cases.append((signed32(integer)*100000,signed32(integer>>32)*100000,(fraction+100000)*100000,1 if ok else 0,raw if ok else 333))
for raw in raws:
 integer=abs(raw)//100000*(-1 if raw<0 else 1);put(integer,raw-integer*100000)
for integer in [-2**63,2**63-1,-92233720368548,-92233720368547,92233720368547,92233720368548]:
 for frac in [-99999,-75809,-75808,0,75807,75808,99999]:put(integer,frac)
inputs=''.join('%d %d %d\n'%c[:3] for c in cases);(out/'inputs.txt').write_text(inputs,encoding='ascii')
p=subprocess.run([str(out/'fixture.exe')],input=inputs.encode(),capture_output=True)
(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
rows=[tuple(map(int,l.split())) for l in p.stdout.decode('ascii').splitlines()]
failed=[{'index':i,'input':list(c[:3]),'expected':list(c[3:]),'observed':list(rows[i]) if i<len(rows) else None} for i,c in enumerate(cases) if i>=len(rows) or rows[i]!=c[3:]]
r={'command':sys.argv,'seed':1202610,'checks':len(cases),'passed':len(cases)-len(failed),'failed':failed,'fixture_exit':p.returncode,'exit':int(bool(failed) or p.returncode!=0)}
(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='failed'},indent=2));raise SystemExit(r['exit'])
