import argparse,json,pathlib,re,sys,zipfile
from urllib.parse import unquote
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def audit(package=None):
    if package:
        with zipfile.ZipFile(package) as z:
            assert z.testzip() is None
            docs={n:z.read(n).decode('utf-8-sig') for n in z.namelist() if n.endswith('.md') and n.startswith(('ai_docs/','test/docs/'))}
    else:docs={p.relative_to(ROOT).as_posix():p.read_text(encoding='utf-8-sig') for d in ['ai_docs','test/docs'] for p in (ROOT/d).rglob('*.md')}
    findings=[];inventory=[]
    for name,text in sorted(docs.items()):
        lines=text.splitlines();inventory.append({'path':name,'lines':len(lines)})
        if len(lines)>300:findings.append({'path':name,'kind':'over_300_lines','observed':len(lines)})
        fence=None;body=[]
        for line in lines:
            m=re.match(r'^\s*(`{3,}|~{3,})',line)
            if m:
                token=m.group(1)[0]
                if fence is None:fence=token
                elif fence==token:fence=None
                continue
            if fence is None and not line.startswith(('    ','\t')):body.append(line)
        if fence:findings.append({'path':name,'kind':'unclosed_fence'})
        for target in re.findall(r'(?<![A-Za-z0-9_./])(?:hoi4plugins/)?(?:test|src)/[A-Za-z0-9_./-]+\.(?:cpp|hpp|py|js|ps1|h|c)(?![A-Za-z0-9])',text):
            if not (ROOT/target.removeprefix('hoi4plugins/')).exists():findings.append({'path':name,'kind':'missing_exact_repo_file','target':target})
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)','\n'.join(body)):
            if target.startswith(('http:','https:','mailto:','codex:','#')):continue
            path=unquote(target.split('#')[0]);candidate=(ROOT/name).parent/path
            try:rel=candidate.resolve().relative_to(ROOT).as_posix()
            except ValueError:rel=None
            present=rel in docs if path.endswith('.md') else candidate.exists()
            if not present:findings.append({'path':name,'kind':'broken_local_link','target':target})
    required={
      'ai_docs/README.md':['TRG_VALUE_DEF','Array64单人交付说明','资源'],
      'ai_docs/09_脚本数值系统/当前状态与复现.md':['137/137','338/338','330/330','资源增长','UI 颜色','已解决'],
      'ai_docs/09_脚本数值系统/变量存储结构.md':['+24','+36','+40','mask=0','542500'],
      'test/docs/README.md':['数值系统测试入口','SHA','Camera_RegisterCommands'],
      'test/docs/numeric_system.md':['verify_array64_api_crash_soak.py','a64soak','历史','资源'],
    }
    for name,tokens in required.items():
        for token in tokens:
            if token not in docs.get(name,''):findings.append({'path':name,'kind':'missing_current_contract','token':token})
    for name,patterns in {
      'ai_docs/README.md':[r'不等于 variable64 比较或数值块参数已完成'],
      'ai_docs/09_脚本数值系统/当前状态与复现.md':[r'公开写入继续关闭',r'数值/block trigger、'],
      'ai_docs/09_脚本数值系统/变量与定点数.md':[r'脚本变量.*值是 32 位有符号整数',r'唯一真正可行的方案'],
    }.items():
        for pattern in patterns:
            if re.search(pattern,docs.get(name,'')):findings.append({'path':name,'kind':'stale_current_claim','pattern':pattern})
    # CLI paths newly advertised to users must exist; do not execute game tests here.
    for name in ['test/docs/numeric_system.md','test/docs/README.md','test/docs/gamedate.md','test/docs/other_modules.md']:
        for path in re.findall(r'test/(?:modules|lib|tools)/[A-Za-z0-9_./-]+\.(?:py|js|ps1)',docs.get(name,'')):
            if not (ROOT/path).exists():findings.append({'path':name,'kind':'missing_script','target':path})
    return {'documents':len(docs),'max_lines':max((r['lines'] for r in inventory),default=0),'findings':findings,'inventory':inventory,'exit':int(bool(findings)),'scope':'UTF-8, line limits, fences, local document links, advertised CLI existence, selected current semantic contracts; external URLs and exhaustive RVA semantics are not automatically certified'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package');p.add_argument('--output');a=p.parse_args();result=audit(a.package)
    if a.output:pathlib.Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='inventory'},ensure_ascii=False,indent=2));raise SystemExit(result['exit'])
