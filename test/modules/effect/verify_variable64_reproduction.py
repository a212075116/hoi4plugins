import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'test/reports/20261012_variable64_reproduction'
if '--dir' in sys.argv:
    OUT=pathlib.Path(sys.argv[sys.argv.index('--dir')+1]).resolve()
expected = {
    'CL': dict(zip(['a'+str(i) for i in range(1,9)], ['1000','1000','555','-1000','10','100','100','7.5'])),
    'MB': dict(zip(['a1','a2','a3','a4','b1','b2'], ['2147483647.99999','2147483647.99999','100000.002','300000.006','2147483647.99999','10'])),
    'DB': dict(zip(['a'+str(i) for i in range(1,7)], ['-2147483647.99999']*4+['-1499996900','-1499996895'])),
    'VN': dict(zip(['v1','v2','v3','v4'], ['1005','1105','2762.5','276.25'])),
    'AR': dict(zip(['a0','a1','a2','b1','b2','c1','c2'], ['100','105','105.25','92233720368547.05','92233720368547','105','107'])),
    'AR2': dict(zip(['s1','s2','s3','s4','s5','s6','s7','sy'], ['100','300','75','-0.5','6.25','3.5','1','75'])),
}
failures = []
rows = []
g = (OUT/'baseline_game.log').read_text(encoding='utf-8',errors='replace')
p = (OUT/'baseline_plugin.log').read_text(encoding='utf-8',errors='replace')
for group, entries in expected.items():
    for key, value in entries.items():
        found = re.findall(r'\b'+group+' '+key+r'=([^\s]+)', g)
        ok = bool(found) and found[-1] == value
        rows.append({'group':group,'key':key,'expected':value,'observed':found,'ok':ok})
        if not ok: failures.append(group+' '+key)
for key,value in {'t0':'12345678901234.56789','t1':'234','t2':'234','t3':'-1235','t4':'1000','t5':'1000','t6':'100','t8':'-1000','t9':'1000'}.items():
    found=re.findall(r'\bM64 '+key+r'=([^\s]+)',g)
    ok=bool(found) and found[-1]==value
    rows.append({'group':'M64','key':key,'expected':value,'observed':found,'ok':ok})
    if not ok: failures.append('M64 '+key)
pollution=[line for line in p.splitlines() if 'temp_army' in line or 'registered [min]' in line or 'registered [max]' in line]
if pollution:failures.append('pollution')
write=re.findall(r'REPRO WRITE (.*)',g)
rg=(OUT/'reload_game.log').read_text(encoding='utf-8',errors='replace') if (OUT/'reload_game.log').exists() else ''
read=re.findall(r'REPRO READ (.*)',rg)
want='marker=12026 big=92233720368546.05 small=1.5 neg=-1.5 zero=0'
if not write or write[-1]!=want:failures.append('write fixture')
if not read or read[-1]!=want:failures.append('reload fixture')
result={'rows':rows,'pollution':pollution,'write':write,'reload':read,'failures':failures}
(OUT/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(rows),'passed':sum(r['ok'] for r in rows),'pollution':len(pollution),'write':write,'reload':read,'failures':failures},ensure_ascii=False,indent=2))
raise SystemExit(bool([f for f in failures if f not in ('write fixture','reload fixture')]) if '--regression-only' in sys.argv else bool(failures))
