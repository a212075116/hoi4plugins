import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import time


parser = argparse.ArgumentParser()
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--helper", type=pathlib.Path, required=True)
parser.add_argument("--report", type=pathlib.Path, required=True)
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parents[2]
game = root.parent
report = args.report.resolve()
report.mkdir(parents=True, exist_ok=True)
def expression(command, text):
    return command + ' "' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
commands = [
    ("completion", "--complete", "set_"),
    ("source", "--command", "achsource"),
    ("compatibility", "--command", "achcompat"),
    ("date", "--command", "setgamedate 1936.1.1.12"),
    ("month", "--command", "addtimeformonths 1"),
    ("hour", "--command", "addtimeforhours -1"),
    ("camera", "--command", "setcamheight 500"),
    ("scalar_set", "--command", expression("eval_effect", "set_variable64 = { var = norm21 value = 12345678901.125 }")),
    ("scalar_add", "--command", expression("eval_effect", "add_to_variable = { var = norm21 value = 2.5 }")),
    ("scalar_log", "--command", expression("eval_effect", "log_variable64 = { var = norm21 }")),
    ("scalar_trigger", "--command", expression("eval_trigger", "plugin_check_variable64 = { var = norm21 value = 12345678903.625 compare = equals }")),
    ("vanilla_last", "--command", expression("eval_effect", "set_variable = { var = norm21 value = 2.5 }")),
    ("vanilla_log", "--command", expression("eval_effect", "log_variable64 = { var = norm21 }")),
    ("array_create", "--command", expression("eval_effect", "create_array64 = { var = norm21a value = 2 }")),
    ("array_set", "--command", expression("eval_effect", "set_array_element64 = { var = norm21a^0 value = 5000000000.125 }")),
    ("array_append", "--command", expression("eval_effect", "append_array64 = { var = norm21a value = 3.5 }")),
    ("array_log", "--command", expression("eval_effect", "log_array64 = { var = norm21a^0 value = 0 }")),
    ("array_trigger", "--command", expression("eval_trigger", "check_array64 = { var = norm21a^num value = 3 compare = equals }")),
    ("language", "--command", expression("eval_effect", 'log = "NORM21 language=[?norm21]"')),
]
ledger_path = report / "commands.json"
rows = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
if any(row["exit"] != 0 for row in rows):
    raise RuntimeError("Recorded command failure must be retained and explicitly corrected before resume; refusing to skip it")
state_path = report / "run_state.json"
if state_path.exists():
    if json.loads(state_path.read_text(encoding="utf-8"))["pid"] != args.pid:
        raise RuntimeError("Report belongs to another PID; use an independent phase directory")
else:
    state_path.write_text(json.dumps(dict(pid=args.pid, helper=str(args.helper.resolve())), indent=2), encoding="utf-8")
for label, flag, text in commands[len(rows):]:
    command = [str(args.helper.resolve()), "--pid", str(args.pid), flag, text]
    p = subprocess.run(command, capture_output=True, timeout=30)
    row = dict(label=label, command=command, stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
    rows.append(row)
    ledger_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(label, p.returncode, row["stdout"].splitlines()[-1] if row["stdout"].splitlines() else "", flush=True)
    if p.returncode:
        raise SystemExit(p.returncode)
time.sleep(0.5)
plugin = game / "reports/mod_loader_tbb.log"
text = plugin.read_text(encoding="utf-8", errors="replace")
marker = "[plugin] thread start, pid=" + str(args.pid)
position = text.rfind(marker)
if position < 0:
    raise RuntimeError("Current PID loader marker missing; refusing stale log verification")
text = text[position:]
(report / "plugin.log").write_bytes(plugin.read_bytes())
document = pathlib.Path.home() / "Documents/Paradox Interactive/Hearts of Iron IV/logs"
for name in ["game.log", "error.log"]:
    if (document / name).exists():
        (report / name).write_bytes((document / name).read_bytes())
values = re.findall(r"\[var64\] log_variable64 norm21 = ([^ ]+)", text)
array = re.findall(r"norm21a\^0=([^\s]+)", text)
by_name = {row["label"]: row for row in rows}
checks = dict(
    command_exits=all(row["exit"] == 0 for row in rows),
    date="Date set 1936.1.1.12" in by_name["date"]["stdout"],
    month="1936.2.1.12" in by_name["month"]["stdout"],
    hour="1936.2.1.11" in by_name["hour"]["stdout"],
    original_source="definitions=293" in by_name["source"]["stdout"] and "installed=1" in by_name["source"]["stdout"],
    scalar_add="12345678903.625" in values,
    vanilla_last="vanilla set reclaimed name [norm21]" in text and "NORM21 language=2.5" in (report / "game.log").read_text(encoding="utf-8", errors="replace"),
    array_value="5000000000.125" in text,
    scalar_trigger=bool(re.search(r"Result\s*=\s*(?:yes|true|1)\b", by_name["scalar_trigger"]["stdout"], re.I)),
    array_trigger=bool(re.search(r"Result\s*=\s*(?:yes|true|1)\b", by_name["array_trigger"]["stdout"], re.I)),
    language="NORM21 language=2.5" in (report / "game.log").read_text(encoding="utf-8", errors="replace"),
)
summary = dict(pid=args.pid, checks=checks, scalar_values=values, array_values=array, legacy_unmarked_log_observation=values[-1] if values else None, helper_sha256=hashlib.sha256(args.helper.read_bytes()).hexdigest(), scope="Independent singleplayer live commands; no save, annex, timers, process termination or scripted achievement gifts", exit=int(not all(checks.values())))
(report / "comparison.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
raise SystemExit(summary["exit"])
