import pathlib,subprocess,json,sys
R=pathlib.Path(__file__).resolve().parents[3];D=R/'test/reports/20261013_achievement_compat';phase=sys.argv[1]
header=pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else R/'src/plugin/SDK_RVA/achievement/achievement_policy.h'
source=r'''
#include <stdio.h>
#include "HEADER"
int main(void){int mask,passed=0,total=0;for(mask=0;mask<512;mask++){
 AchievementEnvironment e={(mask>>0)&1,(mask>>1)&1,(mask>>2)&1,(mask>>3)&1,(mask>>4)&1,(mask>>5)&1};
 int mode=(mask>>6)&1,happened=(mask>>7)&1,already=(mask>>8)&1;
 int expected=e.session_ready&&e.single_player&&e.platform_ready&&e.remaining_possible&&(mode||(e.ironman&&e.checksum_matches))&&happened&&!already;
 int actual=AchievementPolicy_Submit(&e,mode,happened,already);total++;passed+=actual==expected;
 if(actual!=expected)printf("FAIL mask=%d expected=%d actual=%d\n",mask,expected,actual);
 }printf("%d/%d; no Steam calls\n",passed,total);return passed==total?0:1;}
'''.replace('HEADER',header.resolve().as_posix())
cpp=D/(phase+'_policy.c');cpp.write_text(source,encoding='utf-8');exe=D/(phase+'_policy.exe');vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd=f'"{vc}" >nul && cl /nologo /TC /MT "{cpp}" /Fe:"{exe}" /Fo:"{D/(phase+"_policy.obj")}"'
def run(c):
 p=subprocess.run(c,capture_output=True);return dict(command=c,stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode)
build=run('cmd /d /s /c "'+cmd+'"');result=run([str(exe)]) if not build['exit'] else build;x=dict(phase=phase,header=str(header.resolve()),build=build,result=result,scope='Pure policy foundation only; not integrated native eligibility hooks or Steam unlocking')
(D/(phase+'_policy.json')).write_text(json.dumps(x,indent=2),encoding='utf-8');print(json.dumps(x,indent=2));sys.exit(result['exit'])
