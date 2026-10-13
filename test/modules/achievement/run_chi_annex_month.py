import json
import pathlib
import re
import subprocess
import sys
import time

import frida

ROOT = pathlib.Path(__file__).resolve().parents[3]
D = ROOT / "test/reports/20261013_achievement_eligibility"
PID = int(sys.argv[1])
events, commands, snapshots = [], [], []
JS = r'''
const b=Process.getModuleByName('hoi4.exe').base;
for(const rva of [0x2399990,0x2399980])Interceptor.attach(b.add(rva),{onEnter(args){
 try {const vt=args[0].readPointer(),data=args[1];if(data.isNull())return;
 if(vt.equals(b.add(0x2b5bd68)))send({event:'UserStatsStored_t',result:data.add(8).readS32()});
 if(vt.equals(b.add(0x2b5bdb8)))send({event:'UserAchievementStored_t',name:data.add(9).readUtf8String(128).split('\0')[0]});
 }catch(e){send({event:'callback_decode_error',detail:String(e)});}
}});
rpc.exports={snap(){const m=b.add(0x3330460).readPointer(),gs=b.add(0x332f260).readPointer();let rows=[];
 for(const [cat,off,countoff] of [['pending',40,52],['completed',64,76],['excluded',88,100]]){const n=m.add(countoff).readS32(),data=m.add(off).readPointer();for(let i=0;i<n;i++){const a=data.add(i*8).readPointer();const str=Number(a.add(64).readU64().toString())>15?a.add(40).readPointer():a.add(40);rows.push({id:a.add(80).readU16(),name:str.readUtf8String(),category:cat});}}
 return {raw:gs.add(0x468).readS32(),year:gs.add(0x478).readS32(),month:gs.add(0x488).readS32()+1,day:gs.add(0x480).readS32(),ironman:gs.add(0xc0).readU8()&1,flags:Array.from(new Uint8Array(m.add(160).readByteArray(5))),rows};
}};
'''


def execute(command):
    args = [str(ROOT.parent / "hoi4_debug_console.exe"), "--pid", str(PID), "--command", command]
    p = subprocess.run(args, capture_output=True, timeout=30)
    row = dict(command=args, stdout=p.stdout.decode("utf8", errors="replace"), stderr=p.stderr.decode("utf8", errors="replace"), exit=p.returncode)
    commands.append(row)
    print(command, row["stdout"].strip(), flush=True)
    dispatched = bool(re.search(r"transport=1 .*status=0 ok=0", row["stdout"]))
    native_pause = command == "pause_in_hours 744" and "Game will pause after 744 hours." in row["stdout"]
    ambiguous = p.returncode == 1 and dispatched and ((command == "annex all" and len(row["stdout"].strip().splitlines()) == 1) or native_pause)
    row["native_action_result_unspecified"] = bool(ambiguous)
    if p.returncode != 0 and not ambiguous:
        raise RuntimeError("command failed: " + command)
    return row


session = frida.attach(PID)
script = session.create_script(JS)
script.on("message", lambda message, data: events.append(message.get("payload", message)))
script.load()
error = None
try:
    before = script.exports_sync.snap()
    snapshots.append(dict(phase="before", **before))
    assert before["ironman"] == 0, "requires non-Ironman independent CHI test"
    assert before["year"] == 1936 and before["month"] == 1, "744-hour scenario is the first January of the 1936 CHI start"
    status = execute("achievementcompat")
    assert "installed=1 active=1" in status["stdout"], "compatibility must be active before destructive test action"
    if "--resume" not in sys.argv:
        execute("annex all")
    after = script.exports_sync.snap()
    snapshots.append(dict(phase="after-annex", **after))
    target = after["raw"] + 744
    execute("pause_in_hours 744")
    execute("gamespeed 5")
    execute("auto_unpause 5")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        current = script.exports_sync.snap()
        if current["raw"] >= target:
            snapshots.append(dict(phase="after-month", **current))
            break
        time.sleep(2)
    else:
        snapshots.append(dict(phase="timeout", **current))
        raise RuntimeError("normal simulation did not reach 744 hours; no date jump used")
    execute("auto_unpause")
    time.sleep(5)
    execute("achievementcompat")
    execute("achievementstatus")
finally:
    session.detach()
    record = dict(pid=PID, snapshots=snapshots, commands=commands, callbacks=events, real_unlock_authorized=True, conditions_forged=False, account_reset=False, note="Original simulation, no SetGameDate or direct Steam unlock; interceptors only observe native callbacks")
    (D / "chi_annex_month.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
