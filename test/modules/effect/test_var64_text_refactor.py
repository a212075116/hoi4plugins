"""Compile actual private naming/formatting code with a fixed behavior corpus."""
import argparse
import hashlib
import json
import pathlib
import random
import re
import subprocess
import sys

VCVARS = pathlib.Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')


def function(text, name):
    match = re.search(r'^static [^\n]*\b'+re.escape(name)+r'\([^;{]*\)\s*\{', text, re.MULTILINE)
    if not match:
        raise ValueError('Missing function definition: '+name)
    start, opening = match.start(), match.end()-1
    end, depth = opening+1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]+'\n'


def execute(command, cwd, data=None):
    process = subprocess.run(command, cwd=cwd, input=data, capture_output=True, timeout=120)
    return process, dict(command=command, cwd=str(cwd), stdout=process.stdout.decode('utf-8', errors='replace'),
                         stderr=process.stderr.decode('utf-8', errors='replace'), exit=process.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding='utf-8-sig')
    headers = [source.parent/n for n in ['variable64_name.h', 'variable64_text_format.h']]
    if all(p.exists() for p in headers):
        code = ''.join('#include "'+p.as_posix()+'"\n' for p in headers)
    else:
        code = '#define VAR64_HIGH_SUFFIX "_var64h"\n#define VAR64_FRAC_SUFFIX "_var64f"\n#define VAR64_NAME_LIMIT 40u\n'
        code += ''.join(function(text, n) for n in ['Var64_MakeHighPartName', 'Var64_MakeFracPartName'])
        code += text[text.index('#define VAR64_DEC_DIGITS'):text.index('static int Var64_ResolveGameVariable(')]
        code += text[text.index('#define VAR64_FMT_DECIMALS_MAX'):text.index('static void Var64_ParseTextFormat(')]
        code += ''.join(function(text, n) for n in ['Var64_ParseTextFormat', 'Var64_BuildFormattedText'])
    fixture = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
PURE_CODE
static void hex(const void* data,size_t size){const unsigned char* p=data;size_t i;for(i=0;i<size;++i)printf("%02x",p[i]);}
static int passed,total;
static void check(int ok){++total;passed+=!!ok;}
static int sanity(void){
 Var64TextFormat f;char out[96];char name[48];
 Var64_ParseTextFormat(NULL,NULL,&f);Var64_BuildFormattedText(&f,1,25000,out,sizeof(out));check(!strcmp(out,"1.25"));
 Var64_ParseTextFormat("2","2"+1,&f);Var64_BuildFormattedText(&f,1,25000,out,sizeof(out));check(!strcmp(out,"1.25"));
 Var64_ParseTextFormat("%","%"+1,&f);Var64_BuildFormattedText(&f,1,25000,out,sizeof(out));check(!strcmp(out,"125%"));
 Var64_ParseTextFormat("%%","%%"+2,&f);Var64_BuildFormattedText(&f,1,25000,out,sizeof(out));check(!strcmp(out,"1.25%"));
 Var64_ParseTextFormat("=","="+1,&f);Var64_BuildFormattedText(&f,0,0,out,sizeof(out));check(!strcmp(out,"+0"));
 Var64_ParseTextFormat("+","+"+1,&f);Var64_BuildFormattedText(&f,1,0,out,sizeof(out));check((unsigned char)out[0]==0x11&&out[1]=='G');
 check(Var64_MakeHighPartName("value",name,sizeof(name))&&!strcmp(name,"value_var64h"));
 check(Var64_MakeFracPartName("value",name,sizeof(name))&&!strcmp(name,"value_var64f"));
 memset(out,'Z',sizeof(out));Var64_BuildFormattedText(NULL,0,0,out,sizeof(out));check(out[0]=='Z');
 printf("%d/%d text/name sanity checks\n",passed,total);return passed!=total;
}
int main(int argc,char** argv){
 char kind; (void)argv;if(argc>1)return sanity();
 while(scanf_s(" %c",&kind,1)==1){
  if(kind=='F'){
   long long integer,fraction;char spec[32],out[96];int size;Var64TextFormat f;
   if(scanf_s("%lld %lld %31s %d",&integer,&fraction,spec,(unsigned)sizeof(spec),&size)!=4)return 2;
   memset(out,'Z',sizeof(out));Var64_ParseTextFormat(spec,spec+strlen(spec),&f);Var64_BuildFormattedText(&f,integer,fraction,out,size);
   printf("F %d %d %d %d %d %d ",f.decimals,f.useSiUnits,f.percentMode,f.signedPrefix,(int)f.dynamicColour,(int)f.staticColour);hex(out,sizeof(out));puts("");
  }else if(kind=='N'){
   int length,size,which,nulls,ok;char name[64],out[64];
   if(scanf_s("%d %d %d %d",&length,&size,&which,&nulls)!=4)return 2;
   memset(name,'x',sizeof(name));name[length]=0;memset(out,'Z',sizeof(out));
   ok=which?Var64_MakeFracPartName(nulls==1?NULL:name,nulls==2?NULL:out,(unsigned)size):Var64_MakeHighPartName(nulls==1?NULL:name,nulls==2?NULL:out,(unsigned)size);
   printf("N %d ",ok);hex(out,sizeof(out));puts("");
  }else return 2;
 }
 return 0;
}
'''.replace('PURE_CODE', code)
    (output/'fixture.c').write_text(fixture, encoding='ascii')
    compile_command = f'"{VCVARS}" >nul && cl /nologo /W3 /TC /O2 fixture.c /Fe:fixture.exe'
    build_process, build = execute('cmd /d /s /c "'+compile_command+'"', output)
    if build_process.returncode:
        (output/'build_error.json').write_text(json.dumps(build, indent=2), encoding='utf-8')
        print(json.dumps(build, indent=2))
        return build_process.returncode
    specs = ['.','0','1','2','5','9','*','^','%','%%','=','+','-','G','r','*=2','%2+','%%2-','G+','+G','-0','*%5','=^2']
    integers = [-92233720368547,-2147483648,-1000001,-1000,-1,0,1,999,1000,999999,1000000,92233720368547]
    fractions = [-99999,-50000,-1,0,1,25000,99999]
    sizes = [0,7,15,16,32,96]
    cases = [f'F {integer} {fraction} {spec} {size}\n' for integer in integers for fraction in fractions for spec in specs for size in sizes]
    cases += [f'N {length} {size} {which} {nulls}\n' for length in [0,1,8,15,16,31,32,33,39,40,41,48]
              for size in [0,1,7,8,15,16,38,39,40,41,47,48,63,64] for which in [0,1] for nulls in [0,1,2]]
    randomizer = random.Random(20261013)
    alphabet = '012359*^%=+-GRx.'
    for _ in range(4096):
        spec = ''.join(randomizer.choice(alphabet) for _ in range(randomizer.randint(1,10)))
        cases.append(f'F {randomizer.randint(-92233720368547,92233720368547)} {randomizer.randint(-99999,99999)} {spec} {randomizer.choice(sizes)}\n')
    inputs = ''.join(cases).encode('ascii')
    (output/'inputs.txt').write_bytes(inputs)
    process, result = execute([str(output/'fixture.exe')], output, inputs)
    (output/'stdout.txt').write_bytes(process.stdout)
    (output/'stderr.txt').write_bytes(process.stderr)
    sanity_process, sanity = execute([str(output/'fixture.exe'),'--sanity'], output)
    assert process.returncode==0 and len(process.stdout.splitlines())==len(cases)
    assert sanity_process.returncode==0
    result.pop('stdout')
    result['stdout_file'] = str(output/'stdout.txt')
    result['stdout_sha256'] = hashlib.sha256(process.stdout).hexdigest()
    record = dict(source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), seed=20261013,
                  cases=len(cases), input_sha256=hashlib.sha256(inputs).hexdigest(), build=build, result=result, sanity=sanity,
                  scope='Actual pure C naming/formatting, fixed corpus and sanity oracles; no game, native allocator, GUI, persistence or scope resolution calls')
    (output/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
