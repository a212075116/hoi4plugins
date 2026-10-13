import datetime,json,pathlib,subprocess,time

R=pathlib.Path(__file__).resolve().parents[2]
D=R/'test/reports/20261012_variable64_transaction/console_permission'
args=[str(R.parent/'hoi4.exe'),'-gdpr-compliant','-nolauncher','-continuelastsave','-plugin-console']
p=subprocess.Popen(args,cwd=R.parent,creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
record=dict(pid=p.pid,args=args,started=datetime.datetime.now().isoformat(),debug=False,policy='No timer, no kill, no cleanup; launcher remains alive and records actual game exit status')
(D/'monitored_launch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('MONITORED_GAME_PID',p.pid,flush=True)
code=p.wait()
record.update(exit=code,ended=datetime.datetime.now().isoformat())
(D/'monitored_launch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('GAME_EXIT_OBSERVED',code,flush=True)
